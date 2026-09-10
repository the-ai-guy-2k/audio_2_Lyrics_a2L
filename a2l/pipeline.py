"""Primary A2L artifact layout (ACI-A2L-007).

Historical whisper-1 drafts stay under ingest_job/machine_transcription/.
Primary faster-whisper work lives under ingest_job/a2l_pipeline/.
"""

from __future__ import annotations

import json
from pathlib import Path

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIRNAME = "a2l_pipeline"
TRANSCRIPTION_DIRNAME = "machine_transcription"
UNCERTAINTY_DIRNAME = "uncertainty"
STRUCTURE_DIRNAME = "structured_lyrics"
REVIEW_DIRNAME = "human_review"
APPROVED_DIRNAME = "approved_lyrics"
HISTORICAL_WHISPER1_DIRNAME = "machine_transcription"
WHISPER1_JSON_SHA256 = "82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471"
WHISPER1_TXT_SHA256 = "c05fc1227ad6842bb4efa9cf1c375bd392c5fe5361e5a9ad6d49e22864147886"


def ingest_job_dir(sha: str = LOCKED_SHA256, artifact_root: Path | None = None) -> Path:
    root = Path(artifact_root) if artifact_root else ROOT / "artifacts"
    return root / "ingest" / sha


def pipeline_dir(job: Path) -> Path:
    return Path(job) / PIPELINE_DIRNAME


def historical_whisper1_dir(job: Path) -> Path:
    return Path(job) / HISTORICAL_WHISPER1_DIRNAME


def find_ingest_job_dir(start: Path) -> Path | None:
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for parent in [current, *current.parents]:
        if (parent / "ingest_manifest.json").is_file():
            return parent
    return None


def resolve_audio(ingest_job: Path, relative_or_absolute: str) -> Path:
    raw = Path(relative_or_absolute)
    if raw.is_absolute():
        return raw
    return ingest_job / relative_or_absolute


def is_historical_whisper1_path(path: Path, ingest_job: Path) -> bool:
    whisper_root = historical_whisper1_dir(ingest_job).resolve()
    resolved = path.resolve()
    return resolved == whisper_root or whisper_root in resolved.parents


def draft_is_whisper1(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    engine = data.get("engine") or {}
    return engine.get("model") == "whisper-1" or engine.get("technology") == "openai_whisper_api"
