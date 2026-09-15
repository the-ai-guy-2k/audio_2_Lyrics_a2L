"""ACI-A2L-SI-004 isolation checks. Does not require librosa at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_key_mode_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_key_mode_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_and_method() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert "Krumhansl" in module.ENGINE_NAME
    assert module.CANDIDATE_DIR_NAME == "key-mode"
    assert "chroma_cqt" in module.METHOD


def test_c_major_chroma_prefers_c_major() -> None:
    module = _candidate()
    chroma = [0.0] * 12
    chroma[0] = 1.0  # C
    chroma[4] = 0.8  # E
    chroma[7] = 0.9  # G
    result = module.estimate_key_from_chroma(chroma)
    assert result["key"] == "C"
    assert result["mode"] == "major"
    assert result["alternates"][0]["key"] == "C"


def test_a_minor_chroma_prefers_a_minor() -> None:
    module = _candidate()
    chroma = [0.0] * 12
    chroma[9] = 1.0  # A
    chroma[0] = 0.8  # C
    chroma[4] = 0.9  # E
    result = module.estimate_key_from_chroma(chroma)
    assert result["key"] == "A"
    assert result["mode"] == "minor"


def test_refuses_ingest_path() -> None:
    module = _candidate()
    ingest = ROOT / "artifacts" / "ingest" / module.LOCKED_SHA256 / "overwrite.json"
    with pytest.raises(SystemExit):
        module.assert_isolated_output(ingest, module.LOCKED_SHA256)


def test_candidate_output_dir_is_isolated() -> None:
    module = _candidate()
    candidate = (
        ROOT
        / "artifacts"
        / "candidates"
        / module.CANDIDATE_DIR_NAME
        / module.LOCKED_SHA256
        / "key_mode_readable.txt"
    )
    module.assert_isolated_output(candidate, module.LOCKED_SHA256)


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-key-mode-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
