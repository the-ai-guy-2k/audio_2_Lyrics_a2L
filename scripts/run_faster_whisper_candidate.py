"""ACI-A2L-005 isolated faster-whisper large-v3 candidate transcription.

Runs faster-whisper / Whisper large-v3 against the locked mastered WAV.
Does not modify the A2L whisper-1 pipeline or overwrite its artifacts.
Does not continue Parakeet work.
Does not isolate vocals or send text to an LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
LOCKED_SOURCE = Path(
    r"C:\Users\tim\Desktop\Jays_stuff\2026_album\Masters - 24bit_48hz"
    r"\Masters  - 24bit_48hz\01Stomp to MIX MSTR 24bit_48hz.wav"
)
MODEL_SIZE = "large-v3"
MODEL_REPO = "Systran/faster-whisper-large-v3"
DEFAULT_DOWNLOAD_ROOT = Path.home() / ".cache" / "a2l-faster-whisper" / "models"
LOCAL_MODEL_DIR = DEFAULT_DOWNLOAD_ROOT / "large-v3"
EXPECTED_MODEL_BIN_BYTES = 3087284237
ROOT = Path(__file__).resolve().parents[1]
WHISPER_DIR_NAME = "machine_transcription"
PARAKEET_DIR_NAME = "parakeet"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return jsonable(value.item())
        except Exception:
            pass
    return repr(value)


def package_versions() -> dict:
    names = [
        "faster-whisper",
        "ctranslate2",
        "huggingface_hub",
        "tokenizers",
        "onnxruntime",
        "av",
        "tqdm",
    ]
    found = {}
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        return found
    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def hardware_record() -> dict:
    cuda_count = 0
    try:
        import ctranslate2

        cuda_count = int(ctranslate2.get_cuda_device_count())
    except Exception:
        cuda_count = 0
    return {
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "cpu_count": os.cpu_count(),
        "machine": platform.machine(),
        "ctranslate2_cuda_device_count": cuda_count,
        "device": "cpu",
        "compute_type": "int8",
        "nvidia_smi": "not_found_on_path",
        "notes": (
            "No NVIDIA GPU/driver was visible. faster-whisper large-v3 is forced to "
            "CPU with compute_type=int8. Graphics adapter on this workstation is Intel Iris Xe."
        ),
    }


def whisper_paths_intact(sha: str) -> dict:
    job = ROOT / "artifacts" / "ingest" / sha
    whisper_json = job / WHISPER_DIR_NAME / "transcription_draft.json"
    whisper_txt = job / WHISPER_DIR_NAME / "transcription_draft.txt"
    return {
        "whisper_json_exists": whisper_json.is_file(),
        "whisper_txt_exists": whisper_txt.is_file(),
        "whisper_json": str(whisper_json),
        "whisper_txt": str(whisper_txt),
        "whisper_json_sha256": sha256_file(whisper_json) if whisper_json.is_file() else None,
        "whisper_txt_sha256": sha256_file(whisper_txt) if whisper_txt.is_file() else None,
    }


def parakeet_paths_intact(sha: str) -> dict:
    runtime = ROOT / "artifacts" / "candidates" / PARAKEET_DIR_NAME / sha
    evidence = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-005-evidence"
    files = {
        "runtime_raw": runtime / "parakeet_raw.json",
        "runtime_txt": runtime / "parakeet_lyrics.txt",
        "evidence_raw": evidence / "parakeet_raw.json",
        "evidence_txt": evidence / "parakeet_lyrics.txt",
        "evidence_readme": evidence / "README.md",
    }
    record = {}
    for key, path in files.items():
        record[key] = {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else None,
        }
    return record


def assert_not_whisper_path(path: Path, sha: str) -> None:
    whisper_root = (ROOT / "artifacts" / "ingest" / sha / WHISPER_DIR_NAME).resolve()
    resolved = path.resolve()
    if resolved == whisper_root or whisper_root in resolved.parents:
        raise SystemExit(f"Refusing to write into whisper-1 artifact path: {resolved}")


def assert_not_parakeet_path(path: Path, sha: str) -> None:
    roots = [
        (ROOT / "artifacts" / "candidates" / PARAKEET_DIR_NAME / sha).resolve(),
        (ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-005-evidence").resolve(),
    ]
    resolved = path.resolve()
    for root in roots:
        if resolved == root or root in resolved.parents:
            raise SystemExit(f"Refusing to write into Parakeet artifact path: {resolved}")


def decoding_config() -> dict:
    return {
        "language": "en",
        "task": "transcribe",
        "beam_size": 5,
        "best_of": 5,
        "patience": 1,
        "temperature": 0.0,
        "word_timestamps": True,
        "vad_filter": False,
        "condition_on_previous_text": False,
        "without_timestamps": False,
        "initial_prompt": None,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "notes": (
            "language=en is an album/language assumption, not a lyric rewrite. "
            "vad_filter is off because VAD can drop sung vocals on mastered music. "
            "condition_on_previous_text=False reduces repeated-loop hallucination on songs. "
            "temperature=0 for a single deterministic decoding pass."
        ),
    }


def write_readable_txt(path: Path, text: str, segments: list[dict], meta: dict) -> None:
    header = [
        "FASTER-WHISPER LARGE-V3 MACHINE TRANSCRIPTION",
        "STATUS: NON_AUTHORITATIVE_MACHINE_DRAFT",
        "NOT APPROVED LYRICS",
        "No LLM repair was applied.",
        "No vocal isolation was applied.",
        f"engine: faster-whisper {meta.get('faster_whisper_version')}",
        f"ctranslate2: {meta.get('ctranslate2_version')}",
        f"model: {meta.get('model')}",
        f"model_repo: {meta.get('model_repo')}",
        f"device: {meta.get('device')}",
        f"compute_type: {meta.get('compute_type')}",
        f"source_sha256: {meta.get('source_sha256')}",
        f"source_path: {meta.get('source_path')}",
        "",
        "----- BEGIN ACTUAL MACHINE TEXT -----",
        "",
        text or "",
        "",
        "----- TIMED SEGMENTS (ACTUAL MACHINE TEXT) -----",
        "",
    ]
    lines = header
    for item in segments:
        start = item.get("start")
        end = item.get("end")
        seg_text = item.get("text") or ""
        lines.append(f"[{start:.3f} -> {end:.3f}] {seg_text}".rstrip())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def serialize_segment(segment) -> dict:
    words = []
    for word in getattr(segment, "words", None) or []:
        words.append(
            {
                "start": getattr(word, "start", None),
                "end": getattr(word, "end", None),
                "word": getattr(word, "word", None),
                "probability": getattr(word, "probability", None),
            }
        )
    return {
        "id": getattr(segment, "id", None),
        "start": getattr(segment, "start", None),
        "end": getattr(segment, "end", None),
        "text": getattr(segment, "text", None),
        "avg_logprob": getattr(segment, "avg_logprob", None),
        "no_speech_prob": getattr(segment, "no_speech_prob", None),
        "compression_ratio": getattr(segment, "compression_ratio", None),
        "temperature": getattr(segment, "temperature", None),
        "words": words,
    }


def local_model_path(download_root: Path) -> Path | None:
    candidate = download_root / "large-v3"
    model_bin = candidate / "model.bin"
    config = candidate / "config.json"
    if not model_bin.is_file() or not config.is_file():
        return None
    if model_bin.stat().st_size != EXPECTED_MODEL_BIN_BYTES:
        return None
    return candidate


def transcribe(source: Path, download_root: Path) -> dict:
    from faster_whisper import WhisperModel

    captured: list[str] = []
    hw = hardware_record()
    device = hw["device"]
    compute_type = hw["compute_type"]
    cpu_threads = os.cpu_count() or 0
    decode = decoding_config()
    download_root.mkdir(parents=True, exist_ok=True)
    local_dir = local_model_path(download_root)
    model_id = str(local_dir) if local_dir is not None else MODEL_SIZE

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_started = time.perf_counter()
        if local_dir is not None:
            captured.append(f"loading local checkpoint: {local_dir}")
            model = WhisperModel(
                str(local_dir),
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
        else:
            model = WhisperModel(
                MODEL_SIZE,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads,
                download_root=str(download_root),
            )
        load_elapsed = time.perf_counter() - load_started
        started = time.perf_counter()
        segment_iter, info = model.transcribe(
            str(source),
            language=decode["language"],
            task=decode["task"],
            beam_size=decode["beam_size"],
            best_of=decode["best_of"],
            patience=decode["patience"],
            temperature=decode["temperature"],
            word_timestamps=decode["word_timestamps"],
            vad_filter=decode["vad_filter"],
            condition_on_previous_text=decode["condition_on_previous_text"],
            without_timestamps=decode["without_timestamps"],
            compression_ratio_threshold=decode["compression_ratio_threshold"],
            log_prob_threshold=decode["log_prob_threshold"],
            no_speech_threshold=decode["no_speech_threshold"],
        )
        segments = [serialize_segment(segment) for segment in segment_iter]
        elapsed = time.perf_counter() - started
        for item in caught:
            captured.append(warnings.formatwarning(item.message, item.category, item.filename, item.lineno))

    text = " ".join((item.get("text") or "").strip() for item in segments).strip()
    info_payload = {
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "duration_after_vad": getattr(info, "duration_after_vad", None),
        "transcription_options": jsonable(getattr(info, "transcription_options", None)),
        "vad_options": jsonable(getattr(info, "vad_options", None)),
    }
    return {
        "text": text,
        "segments": segments,
        "info": info_payload,
        "warnings": captured,
        "processing_seconds": elapsed,
        "model_load_seconds": load_elapsed,
        "device": device,
        "compute_type": compute_type,
        "cpu_threads": cpu_threads,
        "download_root": str(download_root),
        "model_loaded_from": model_id,
        "audio_input": str(source),
        "audio_resampled_on_disk": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-005 faster-whisper large-v3 candidate")
    parser.add_argument("--source", type=Path, default=LOCKED_SOURCE)
    parser.add_argument("--download-root", type=Path, default=DEFAULT_DOWNLOAD_ROOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/faster-whisper-large-v3/<sha256>/",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source
    if not source.is_file():
        print(f"FAIL: locked source not found: {source}")
        return 1

    before_sha = sha256_file(source)
    if before_sha != LOCKED_SHA256:
        print(f"FAIL: locked source SHA mismatch: {before_sha}")
        return 1

    whisper_before = whisper_paths_intact(LOCKED_SHA256)
    parakeet_before = parakeet_paths_intact(LOCKED_SHA256)
    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / "faster-whisper-large-v3" / LOCKED_SHA256
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "faster_whisper_large_v3_raw.json"
    txt_path = out_dir / "faster_whisper_large_v3_lyrics.txt"
    run_path = out_dir / "faster_whisper_large_v3_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_not_whisper_path(path, LOCKED_SHA256)
        assert_not_parakeet_path(path, LOCKED_SHA256)

    versions = package_versions()
    hw = hardware_record()
    errors = []
    result: dict = {}
    started_utc = datetime.now(timezone.utc).isoformat()
    try:
        result = transcribe(source, args.download_root)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    after_sha = sha256_file(source)
    whisper_after = whisper_paths_intact(LOCKED_SHA256)
    parakeet_after = parakeet_paths_intact(LOCKED_SHA256)
    whisper_unchanged = (
        whisper_before.get("whisper_json_sha256") == whisper_after.get("whisper_json_sha256")
        and whisper_before.get("whisper_txt_sha256") == whisper_after.get("whisper_txt_sha256")
    )
    parakeet_unchanged = parakeet_before == parakeet_after

    fw_version = versions.get("faster-whisper")
    ct2_version = versions.get("ctranslate2")
    text = result.get("text", "")
    segments = result.get("segments") or []
    raw_payload = {
        "candidate": "ACI-A2L-005",
        "engine": "faster-whisper",
        "model": MODEL_SIZE,
        "model_repo": MODEL_REPO,
        "faster_whisper_version": fw_version,
        "ctranslate2_version": ct2_version,
        "usable_as_approved_lyrics": False,
        "approval_status": "NOT_APPROVED",
        "llm_repair_applied": False,
        "vocal_isolation": False,
        "source_path": str(source),
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "source_bytes": source.stat().st_size,
        "device": result.get("device") or hw["device"],
        "compute_type": result.get("compute_type") or hw["compute_type"],
        "cpu_threads": result.get("cpu_threads"),
        "decoding": decoding_config(),
        "processing_seconds": result.get("processing_seconds"),
        "model_load_seconds": result.get("model_load_seconds"),
        "package_versions": versions,
        "hardware": hw,
        "warnings": result.get("warnings") or [],
        "errors": errors,
        "audio_input": result.get("audio_input") or str(source),
        "audio_resampled_on_disk": result.get("audio_resampled_on_disk", False),
        "download_root": result.get("download_root") or str(args.download_root),
        "info": result.get("info"),
        "text": text,
        "segments": segments,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        text,
        segments,
        {
            "faster_whisper_version": fw_version,
            "ctranslate2_version": ct2_version,
            "model": MODEL_SIZE,
            "model_repo": MODEL_REPO,
            "device": raw_payload["device"],
            "compute_type": raw_payload["compute_type"],
            "source_sha256": after_sha,
            "source_path": str(source),
        },
    )

    evidence_dir = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-005-faster-whisper-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, evidence_dir / "faster_whisper_large_v3_raw.json")
    shutil.copy2(txt_path, evidence_dir / "faster_whisper_large_v3_lyrics.txt")

    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not errors and bool(text),
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": before_sha == after_sha == LOCKED_SHA256,
        "whisper_baseline_intact": whisper_unchanged and whisper_after["whisper_json_exists"],
        "parakeet_artifacts_intact": parakeet_unchanged,
        "whisper_before": whisper_before,
        "whisper_after": whisper_after,
        "parakeet_before": parakeet_before,
        "parakeet_after": parakeet_after,
        "errors": errors,
        "processing_seconds": result.get("processing_seconds"),
        "model_load_seconds": result.get("model_load_seconds"),
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, evidence_dir / "faster_whisper_large_v3_run.json")

    print(json.dumps(run_payload, indent=2))
    print("FASTER-WHISPER LARGE-V3 READABLE OUTPUT:")
    print(str(txt_path.resolve()))
    if errors:
        return 1
    if after_sha != LOCKED_SHA256:
        print("FAIL: source SHA changed")
        return 1
    if not whisper_unchanged:
        print("FAIL: whisper-1 artifacts changed")
        return 1
    if not parakeet_unchanged:
        print("FAIL: Parakeet artifacts changed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
