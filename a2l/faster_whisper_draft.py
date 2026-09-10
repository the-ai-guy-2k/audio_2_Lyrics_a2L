"""Build a transcription draft from faster-whisper large-v3 candidate output.

Uses existing uncertainty and structuring. Does not call OpenAI whisper-1.
Does not overwrite the whisper-1 baseline under artifacts/ingest/<sha>/machine_transcription/.
"""

from __future__ import annotations

import json
from pathlib import Path

from a2l.engines import EngineResult, EngineSegment
from a2l.errors import ReviewError
from a2l.signal import pcm_energy
from a2l.structure import structure_lyrics
from a2l.transcribe import build_draft
from a2l.uncertainty import evaluate_uncertainty

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
ROOT = Path(__file__).resolve().parents[1]
WHISPER_DIR_NAME = "machine_transcription"


def candidate_job_dir(sha: str = LOCKED_SHA256) -> Path:
    return ROOT / "artifacts" / "candidates" / "faster-whisper-large-v3" / sha


def default_raw_path(sha: str = LOCKED_SHA256) -> Path:
    return candidate_job_dir(sha) / "faster_whisper_large_v3_raw.json"


def default_ingest_manifest(sha: str = LOCKED_SHA256) -> Path:
    return ROOT / "artifacts" / "ingest" / sha / "ingest_manifest.json"


def assert_not_whisper_baseline(path: Path, sha: str) -> None:
    whisper_root = (ROOT / "artifacts" / "ingest" / sha / WHISPER_DIR_NAME).resolve()
    resolved = path.resolve()
    if resolved == whisper_root or whisper_root in resolved.parents:
        raise ReviewError("WHISPER_PATH_REFUSED", f"Refusing to write into whisper-1 artifact path: {resolved}")


def prepare_structured_from_faster_whisper(
    raw_path: str | Path | None = None,
    ingest_manifest_path: str | Path | None = None,
    sha: str = LOCKED_SHA256,
) -> dict:
    raw_path = Path(raw_path) if raw_path else default_raw_path(sha)
    ingest_manifest_path = Path(ingest_manifest_path) if ingest_manifest_path else default_ingest_manifest(sha)
    if not raw_path.is_file():
        raise ReviewError("FASTER_WHISPER_RAW_NOT_FOUND", f"faster-whisper raw artifact not found: {raw_path}")
    if not ingest_manifest_path.is_file():
        raise ReviewError("INGEST_MANIFEST_NOT_FOUND", f"Ingest manifest not found: {ingest_manifest_path}")

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if raw.get("model") != "large-v3" or raw.get("engine") != "faster-whisper":
        raise ReviewError(
            "ENGINE_MISMATCH",
            "Human review consumes faster-whisper large-v3 output, not whisper-1.",
        )
    manifest = json.loads(ingest_manifest_path.read_text(encoding="utf-8"))
    ingest_job = ingest_manifest_path.parent
    source_path = ingest_job / manifest["authoritative_source"]["relative_path"]
    working_path = ingest_job / manifest["derived_working"]["relative_path"]
    if not working_path.is_file():
        raise ReviewError("WORKING_AUDIO_MISSING", f"CONTROL-A working WAV not found: {working_path}")

    job_dir = candidate_job_dir(sha)
    draft_dir = job_dir_transcription(job_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "transcription_draft.json"
    assert_not_whisper_baseline(draft_path, sha)

    segments = []
    for item in raw.get("segments") or []:
        segments.append(
            EngineSegment(
                start_seconds=float(item.get("start") or 0),
                end_seconds=float(item.get("end") or 0),
                text=str(item.get("text") or ""),
                avg_logprob=item.get("avg_logprob"),
                no_speech_prob=item.get("no_speech_prob"),
                compression_ratio=item.get("compression_ratio"),
            )
        )
    engine_result = EngineResult(
        technology="faster-whisper",
        model="large-v3",
        text=str(raw.get("text") or ""),
        language=(raw.get("info") or {}).get("language"),
        segments=tuple(segments),
        configuration={
            "device": raw.get("device"),
            "compute_type": raw.get("compute_type"),
            "decoding": raw.get("decoding") or {},
            "vocal_isolation": "not_applied",
            "candidate": "ACI-A2L-005",
            "faster_whisper_version": raw.get("faster_whisper_version"),
            "ctranslate2_version": raw.get("ctranslate2_version"),
        },
    )
    energy = pcm_energy(working_path)
    draft = build_draft(
        ingest_manifest=manifest,
        ingest_manifest_path=ingest_manifest_path,
        working_path=working_path,
        energy=energy,
        engine_result=engine_result,
    )
    draft["input"]["working_audio"] = str(working_path.resolve())
    draft["input"]["authoritative_source"] = str(source_path.resolve())
    draft["notes"] = list(draft.get("notes") or []) + [
        "Primary transcription for human review is faster-whisper large-v3.",
        "This draft does not replace the whisper-1 baseline.",
    ]
    draft_path.write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (draft_dir / "transcription_draft.txt").write_text(
        "A2L MACHINE TRANSCRIPTION DRAFT — NOT APPROVED LYRICS\n"
        "Engine: faster-whisper / large-v3\n\n"
        f"{draft['engine_text']}\n",
        encoding="utf-8",
    )

    uncertainty = evaluate_uncertainty(draft_path)
    structured = structure_lyrics(uncertainty.report_path)
    return {
        "raw_path": str(raw_path.resolve()),
        "draft_path": str(structured.draft_path),
        "text_path": str(structured.text_path),
        "uncertainty_path": str(uncertainty.report_path),
        "engine": "faster-whisper",
        "model": "large-v3",
        "ingest_job_id": sha,
    }


def job_dir_transcription(job_dir: Path) -> Path:
    return job_dir / WHISPER_DIR_NAME
