"""ACI-A2L-SI-002 isolation checks. Does not require all-in-one-infer at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_all_in_one_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_all_in_one_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_matches_fixed_song_record() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert module.ENGINE_NAME == "all-in-one-infer"
    assert module.DEFAULT_MODEL == "harmonix-all"
    assert module.ANALYSIS_PATH == "mix-as-stems"
    assert module.CANDIDATE_DIR_NAME == "all-in-one-infer"


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-all-in-one-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_refuses_ingest_and_approved_lyric_paths() -> None:
    module = _candidate()
    ingest = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256 / "overwrite.json"
    approved = (
        ROOT
        / "docs"
        / "nebula"
        / "artifacts"
        / "aci-a2l-009-evidence"
        / "approved_lyrics.txt"
    )
    with pytest.raises(SystemExit):
        module.assert_isolated_output(ingest, module.LOCKED_SHA256)
    if approved.exists():
        with pytest.raises(SystemExit):
            module.assert_isolated_output(approved, module.LOCKED_SHA256)


def test_candidate_output_dir_is_isolated() -> None:
    module = _candidate()
    candidate = (
        ROOT
        / "artifacts"
        / "candidates"
        / module.CANDIDATE_DIR_NAME
        / module.LOCKED_SHA256
        / "all_in_one_readable.txt"
    )
    module.assert_isolated_output(candidate, module.LOCKED_SHA256)
    ingest = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256
    assert ingest.resolve() not in candidate.resolve().parents


def test_format_timestamp_preserves_analyzer_seconds() -> None:
    module = _candidate()
    assert module.format_timestamp(0) == "00:00"
    assert module.format_timestamp(12.9) == "00:12"
    assert module.format_timestamp(65) == "01:05"


def test_prepare_analysis_wav_is_documented_as_derived() -> None:
    module = _candidate()
    assert "24-bit" in module.prepare_analysis_wav.__doc__
    assert "mmap" in module.prepare_analysis_wav.__doc__
