"""ACI-A2L-011 isolation checks. Does not require NeMo at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_nvidia_parakeet_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_nvidia_parakeet_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_matches_fixed_song_record() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert module.PARAKEET_MODEL == "nvidia/parakeet-tdt-0.6b-v2"
    assert module.CANDIDATE_DIR_NAME == "nvidia-parakeet"


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-nvidia-parakeet-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_refuses_primary_pipeline_path() -> None:
    module = _candidate()
    pipeline = (
        ROOT
        / "artifacts"
        / "ingest"
        / module.LOCKED_SHA256
        / module.PIPELINE_DIR_NAME
        / "machine_transcription"
        / "overwrite.json"
    )
    with pytest.raises(SystemExit):
        module.assert_isolated_output(pipeline, module.LOCKED_SHA256)


def test_refuses_whisper1_and_approved_paths() -> None:
    module = _candidate()
    whisper = (
        ROOT
        / "artifacts"
        / "ingest"
        / module.LOCKED_SHA256
        / module.WHISPER1_DIR_NAME
        / "overwrite.json"
    )
    approved = (
        ROOT
        / "artifacts"
        / "ingest"
        / module.LOCKED_SHA256
        / module.PIPELINE_DIR_NAME
        / "approved_lyrics"
        / "approved_lyrics.txt"
    )
    review = (
        ROOT
        / "artifacts"
        / "ingest"
        / module.LOCKED_SHA256
        / module.PIPELINE_DIR_NAME
        / "human_review"
        / "reviewed_lyric_draft.json"
    )
    with pytest.raises(SystemExit):
        module.assert_isolated_output(whisper, module.LOCKED_SHA256)
    with pytest.raises(SystemExit):
        module.assert_isolated_output(approved, module.LOCKED_SHA256)
    with pytest.raises(SystemExit):
        module.assert_isolated_output(review, module.LOCKED_SHA256)


def test_refuses_faster_whisper_candidate_path() -> None:
    module = _candidate()
    faster = (
        ROOT
        / "artifacts"
        / "candidates"
        / module.FASTER_WHISPER_DIR_NAME
        / module.LOCKED_SHA256
        / "faster_whisper_large_v3_lyrics.txt"
    )
    with pytest.raises(SystemExit):
        module.assert_isolated_output(faster, module.LOCKED_SHA256)


def test_candidate_output_dir_is_isolated() -> None:
    module = _candidate()
    candidate = (
        ROOT
        / "artifacts"
        / "candidates"
        / module.CANDIDATE_DIR_NAME
        / module.LOCKED_SHA256
        / "nvidia_parakeet_lyrics.txt"
    )
    module.assert_isolated_output(candidate, module.LOCKED_SHA256)
    pipeline = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256 / module.PIPELINE_DIR_NAME
    whisper = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256 / module.WHISPER1_DIR_NAME
    faster = ROOT / "artifacts" / "candidates" / module.FASTER_WHISPER_DIR_NAME / module.LOCKED_SHA256
    assert pipeline.resolve() not in candidate.resolve().parents
    assert whisper.resolve() not in candidate.resolve().parents
    assert faster.resolve() not in candidate.resolve().parents
