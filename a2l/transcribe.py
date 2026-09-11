"""CONTROL-A transcription from an ACI-ATL-001 ingest manifest.

FLAG IT — DO NOT INVENT IT.
Machine output is a non-authoritative draft. It is never approved lyrics.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from a2l.errors import TranscriptionError
from a2l.engines import EngineResult, EngineSegment, FasterWhisperEngine, TranscriptionEngine
from a2l.pipeline import (
    PARAKEET_PIPELINE_DIRNAME,
    PIPELINE_DIRNAME,
    TRANSCRIPTION_DIRNAME,
    is_historical_whisper1_path,
    pipeline_dir,
    pipeline_dirname_for_engine,
)
from a2l.signal import pcm_energy
from a2l.wav import sha256_bytes

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-ATL-002"
DRAFT_DIRNAME = TRANSCRIPTION_DIRNAME
DRAFT_FILENAME = "transcription_draft.json"
DRAFT_TEXT_FILENAME = "transcription_draft.txt"
AUTHORITY = "NON_AUTHORITATIVE_MACHINE_DRAFT"
APPROVAL_STATUS = "NOT_APPROVED"

LOW_LOGPROB = -1.0
HIGH_NO_SPEECH = 0.6
HIGH_COMPRESSION = 2.4


@dataclass(frozen=True)
class TranscriptionResult:
    job_id: str
    draft_path: Path
    text_path: Path
    working_path: Path
    source_path: Path
    draft: dict


def default_transcription_engine() -> TranscriptionEngine:
    return FasterWhisperEngine()


def transcribe_from_manifest(
    manifest_path: str | Path,
    engine: TranscriptionEngine | None = None,
) -> TranscriptionResult:
    manifest_path = Path(manifest_path)
    manifest = _load_ingest_manifest(manifest_path)
    job_dir = manifest_path.parent
    working_path = job_dir / manifest["derived_working"]["relative_path"]
    source_path = job_dir / manifest["authoritative_source"]["relative_path"]

    _assert_control_a(manifest)
    _assert_file_hash(working_path, manifest["derived_working"]["sha256"], "WORKING_HASH_MISMATCH")
    _assert_file_hash(source_path, manifest["authoritative_source"]["sha256"], "SOURCE_HASH_MISMATCH")

    source_before = source_path.read_bytes()
    working_before = working_path.read_bytes()

    energy = pcm_energy(working_path)
    active_engine = engine or default_transcription_engine()
    started = time.perf_counter()
    engine_result = active_engine.transcribe(working_path)
    elapsed = round(time.perf_counter() - started, 2)

    if source_path.read_bytes() != source_before:
        raise TranscriptionError("SOURCE_MUTATED", "Authoritative source changed during transcription.")
    if working_path.read_bytes() != working_before:
        raise TranscriptionError("WORKING_MUTATED", "CONTROL-A working audio changed during transcription.")

    draft = build_draft(
        ingest_manifest=manifest,
        ingest_manifest_path=manifest_path,
        working_path=working_path,
        energy=energy,
        engine_result=engine_result,
    )
    draft["transcription_seconds"] = elapsed
    configuration = dict(draft["engine"].get("configuration") or {})
    configuration["transcription_seconds"] = elapsed
    draft["engine"]["configuration"] = configuration
    dirname = pipeline_dirname_for_engine(active_engine)
    draft["pipeline_dirname"] = dirname
    draft_dir = pipeline_dir(job_dir, dirname) / DRAFT_DIRNAME
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / DRAFT_FILENAME
    text_path = draft_dir / DRAFT_TEXT_FILENAME
    if is_historical_whisper1_path(draft_path, job_dir):
        raise TranscriptionError(
            "WHISPER_PATH_REFUSED",
            f"Refusing to overwrite historical whisper-1 artifacts: {draft_path}",
        )
    primary_root = pipeline_dir(job_dir, PIPELINE_DIRNAME).resolve()
    if dirname == PARAKEET_PIPELINE_DIRNAME and (
        draft_path.resolve() == primary_root or primary_root in draft_path.resolve().parents
    ):
        raise TranscriptionError(
            "PRIMARY_PATH_REFUSED",
            "Parakeet must not overwrite the primary faster-whisper pipeline.",
        )
    draft_path.write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(_human_readable_draft(draft), encoding="utf-8")

    return TranscriptionResult(
        job_id=manifest["job_id"],
        draft_path=draft_path.resolve(),
        text_path=text_path.resolve(),
        working_path=working_path.resolve(),
        source_path=source_path.resolve(),
        draft=draft,
    )


def build_draft(
    *,
    ingest_manifest: dict,
    ingest_manifest_path: Path,
    working_path: Path,
    energy: dict,
    engine_result: EngineResult,
) -> dict:
    job_flags: list[str] = ["NOT_APPROVED", "NON_AUTHORITATIVE"]
    segments = [_flag_segment(segment, energy) for segment in engine_result.segments]
    engine_text = engine_result.text.strip()

    if energy.get("no_signal"):
        job_flags.append("NO_SIGNAL")
        if engine_text:
            job_flags.append("ENGINE_TEXT_ON_NO_SIGNAL")
            job_flags.append("DO_NOT_TREAT_AS_LYRICS")

    if not engine_text:
        job_flags.append("NO_RECOVERABLE_SPEECH")

    if any("LOW_CONFIDENCE" in item["flags"] for item in segments):
        job_flags.append("LOW_CONFIDENCE_SEGMENTS")
    if any("NO_SPEECH_LIKELY" in item["flags"] for item in segments):
        job_flags.append("NO_SPEECH_LIKELY")
    if any("POSSIBLE_HALLUCINATION" in item["flags"] for item in segments):
        job_flags.append("POSSIBLE_HALLUCINATION")

    job_flags = sorted(set(job_flags))
    trusted_as_lyrics = False

    architecture_status = "ACI-ATL-002_BASELINE_NOT_GVCA_LOCKED"
    if engine_result.technology == "faster-whisper":
        architecture_status = "ACI-A2L-007_PRIMARY_FASTER_WHISPER_LARGE_V3"
    elif "parakeet" in engine_result.technology or "parakeet" in engine_result.model:
        architecture_status = "ACI-A2L-012_ALTERNATE_NVIDIA_PARAKEET_TDT_0_6B_V2"
        job_flags.append("NO_ENGINE_CONFIDENCE")
        job_flags.append("ALTERNATE_ENGINE")
        job_flags = sorted(set(job_flags))

    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "approval_status": APPROVAL_STATUS,
        "usable_as_approved_lyrics": trusted_as_lyrics,
        "control_baseline": ingest_manifest["control_baseline"],
        "ingest_job_id": ingest_manifest["job_id"],
        "ingest_manifest": ingest_manifest_path.name,
        "input": {
            "working_audio": ingest_manifest["derived_working"]["relative_path"],
            "working_sha256": ingest_manifest["derived_working"]["sha256"],
            "authoritative_source": ingest_manifest["authoritative_source"]["relative_path"],
            "preprocessing": ingest_manifest["derived_working"]["preprocessing"],
            "vocal_isolation": ingest_manifest["derived_working"]["vocal_isolation"],
            "audio": ingest_manifest["audio"],
        },
        "engine": {
            "technology": engine_result.technology,
            "model": engine_result.model,
            "configuration": engine_result.configuration,
            "language": engine_result.language,
            "architecture_status": architecture_status,
        },
        "signal": energy,
        "flags": job_flags,
        "segments": segments,
        "engine_text": engine_result.text,
        "draft_text": engine_result.text,
        "notes": [
            "Machine transcription is a draft only.",
            "FLAG IT — DO NOT INVENT IT: uncertain or no-signal output is flagged, not rewritten into lyrics.",
            "Do not treat this file as approved lyrics.",
            "Vocal isolation was not applied.",
            *(
                [
                    "Primary engine is faster-whisper / Whisper large-v3 (ACI-A2L-007).",
                    "Historical whisper-1 artifacts are not overwritten.",
                ]
                if engine_result.technology == "faster-whisper"
                else []
            ),
            *(
                [
                    "Alternate engine is NVIDIA Parakeet TDT 0.6B v2 (ACI-A2L-012).",
                    "Parakeet does not provide Whisper-style logprob/no-speech/compression signals.",
                    "Missing confidence is recorded as NO_ENGINE_CONFIDENCE, not invented.",
                    "Stereo channels were averaged in memory. That is not vocal isolation.",
                    "Primary faster-whisper artifacts are not overwritten.",
                ]
                if "parakeet" in engine_result.technology or "parakeet" in engine_result.model
                else []
            ),
        ],
    }


def _flag_segment(segment: EngineSegment, energy: dict) -> dict:
    flags: list[str] = []
    text = segment.text.strip()
    if energy.get("no_signal") and text:
        flags.append("ENGINE_TEXT_ON_NO_SIGNAL")
        flags.append("DO_NOT_TREAT_AS_LYRICS")
    if segment.avg_logprob is not None and segment.avg_logprob < LOW_LOGPROB:
        flags.append("LOW_CONFIDENCE")
    if segment.no_speech_prob is not None and segment.no_speech_prob >= HIGH_NO_SPEECH:
        flags.append("NO_SPEECH_LIKELY")
    if segment.compression_ratio is not None and segment.compression_ratio > HIGH_COMPRESSION:
        flags.append("POSSIBLE_HALLUCINATION")
    if not text:
        flags.append("EMPTY_SEGMENT")
    if (
        segment.avg_logprob is None
        and segment.no_speech_prob is None
        and segment.compression_ratio is None
    ):
        flags.append("NO_ENGINE_CONFIDENCE")
    return {
        "start_seconds": segment.start_seconds,
        "end_seconds": segment.end_seconds,
        "text": segment.text,
        "avg_logprob": segment.avg_logprob,
        "no_speech_prob": segment.no_speech_prob,
        "compression_ratio": segment.compression_ratio,
        "flags": sorted(set(flags)),
    }


def _load_ingest_manifest(path: Path) -> dict:
    if not path.is_file():
        raise TranscriptionError("MANIFEST_NOT_FOUND", f"Ingest manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TranscriptionError("MANIFEST_INVALID", "ingest_manifest.json is not valid JSON.") from exc
    required = ["job_id", "control_baseline", "authoritative_source", "derived_working", "audio"]
    missing = [key for key in required if key not in manifest]
    if missing:
        raise TranscriptionError("MANIFEST_INVALID", f"Ingest manifest missing fields: {', '.join(missing)}")
    for role in ("authoritative_source", "derived_working"):
        for field in ("relative_path", "sha256"):
            if field not in manifest[role]:
                raise TranscriptionError("MANIFEST_INVALID", f"{role}.{field} is required.")
    return manifest


def _assert_control_a(manifest: dict) -> None:
    if manifest.get("control_baseline") != "CONTROL_A":
        raise TranscriptionError(
            "NOT_CONTROL_A",
            "ACI-ATL-002 consumes untreated CONTROL-A working audio only.",
        )
    working = manifest["derived_working"]
    if working.get("vocal_isolation") != "not_applied":
        raise TranscriptionError(
            "VOCAL_ISOLATION_NOT_AUTHORIZED",
            "Vocal isolation is not authorized for ACI-ATL-002.",
        )
    if working.get("preprocessing") != "none":
        raise TranscriptionError(
            "PREPROCESSED_AUDIO_NOT_AUTHORIZED",
            "ACI-ATL-002 must use untreated CONTROL-A audio.",
        )


def _assert_file_hash(path: Path, expected: str, code: str) -> None:
    if not path.is_file():
        raise TranscriptionError("WORKING_AUDIO_MISSING", f"Expected audio artifact missing: {path}")
    digest = sha256_bytes(path.read_bytes())
    if digest != expected:
        raise TranscriptionError(code, f"SHA-256 mismatch for {path.name}.")


def _human_readable_draft(draft: dict) -> str:
    flags = ", ".join(draft["flags"])
    return (
        "A2L MACHINE TRANSCRIPTION DRAFT — NOT APPROVED LYRICS\n"
        f"Authority: {draft['authority']}\n"
        f"Approval: {draft['approval_status']}\n"
        f"Flags: {flags}\n"
        f"Engine: {draft['engine']['technology']} / {draft['engine']['model']}\n"
        "\n"
        "--- engine_text ---\n"
        f"{draft['engine_text']}\n"
    )
