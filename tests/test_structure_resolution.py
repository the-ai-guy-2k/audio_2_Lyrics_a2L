"""ACI-A2L-SI-003 isolation checks. Does not require all-in-one-infer at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_structure_resolution.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_structure_resolution", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preserves_si002_rhythm_constants() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.sio.LOCKED_SHA256 in record
    assert module.ENGINE_NAME == "all-in-one-infer"
    assert module.DEFAULT_MODEL == "harmonix-all"
    assert module.ANALYSIS_PATH == "official-mixed-htdemucs-diagnostic"
    assert module.INVESTIGATION["A_mixed_path_without_separation"]["result"] == "not_available"
    assert module.INVESTIGATION["B_config_without_fabricating_stems"]["result"] == "not_available"
    assert module.INVESTIGATION["source_separation"] == "DIAGNOSTIC"
    assert module.INVESTIGATION["not_accepted_a2l_capability"] is True
    assert module.INVESTIGATION["C_alternate_structure_engine"]["result"] == "not_started"


def test_refuses_ingest_and_si002_evidence_paths() -> None:
    module = _candidate()
    ingest = ROOT / "artifacts" / "ingest" / module.sio.LOCKED_SHA256 / "overwrite.json"
    with pytest.raises(SystemExit):
        module.sio.assert_isolated_output(ingest, module.sio.LOCKED_SHA256)
    si002 = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence" / "all_in_one_raw.json"
    assert module.SI002_EVIDENCE.name == "aci-a2l-si-002-evidence"
    assert si002.parent == module.SI002_EVIDENCE


def test_structure_row_format() -> None:
    module = _candidate()
    rows = module.format_structure_rows(
        {
            "segments": [
                {"start": 0, "end": 12.4, "label": "intro"},
                {"start": 40, "end": 63, "label": "chorus"},
            ]
        }
    )
    assert rows == ["00:00-00:12 | intro", "00:40-01:03 | chorus"]


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-si-003-isolation")
    assert module.sio.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
