"""ACI-A2L-005 isolation checks. Does not require faster-whisper at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_faster_whisper_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_faster_whisper_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_matches_fixed_song_record() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert module.MODEL_SIZE == "large-v3"
    assert module.MODEL_REPO == "Systran/faster-whisper-large-v3"


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-faster-whisper-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_refuses_whisper_artifact_path() -> None:
    module = _candidate()
    whisper = (
        ROOT
        / "artifacts"
        / "ingest"
        / module.LOCKED_SHA256
        / module.WHISPER_DIR_NAME
        / "overwrite.json"
    )
    with pytest.raises(SystemExit):
        module.assert_not_whisper_path(whisper, module.LOCKED_SHA256)


def test_refuses_parakeet_artifact_path() -> None:
    module = _candidate()
    parakeet = (
        ROOT
        / "artifacts"
        / "candidates"
        / "parakeet"
        / module.LOCKED_SHA256
        / "parakeet_lyrics.txt"
    )
    with pytest.raises(SystemExit):
        module.assert_not_parakeet_path(parakeet, module.LOCKED_SHA256)


def test_candidate_output_dir_is_isolated() -> None:
    module = _candidate()
    candidate = (
        ROOT
        / "artifacts"
        / "candidates"
        / "faster-whisper-large-v3"
        / module.LOCKED_SHA256
        / "faster_whisper_large_v3_lyrics.txt"
    )
    module.assert_not_whisper_path(candidate, module.LOCKED_SHA256)
    module.assert_not_parakeet_path(candidate, module.LOCKED_SHA256)
    whisper = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256 / module.WHISPER_DIR_NAME
    parakeet = ROOT / "artifacts" / "candidates" / "parakeet" / module.LOCKED_SHA256
    assert whisper.resolve() not in candidate.resolve().parents
    if parakeet.exists():
        assert parakeet.resolve() not in candidate.resolve().parents
