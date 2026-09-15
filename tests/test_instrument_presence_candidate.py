"""ACI-A2L-SI-010 isolation checks. Does not require PANNs weights at test time."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_instrument_presence_candidate.py"
SI009 = ROOT / "scripts" / "run_instrumentation_genre_candidate.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_instrument_presence_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_checkpoint_and_license() -> None:
    module = _module()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module._si007.LOCKED_SHA256 in record
    assert module.CHECKPOINT_NAME == "Cnn14_mAP=0.431.pth"
    assert module.LICENSE_DECLARED == "cc-by-4.0"
    assert "cc-by-4.0" in module.ALLOWED_LICENSES
    assert module.OPERATING_POINT == 0.50
    assert module.CANDIDATE_DIR_NAME == "panns-instrument-presence"
    assert module.EVIDENCE_DIR.name == "aci-a2l-si-010-evidence"
    assert "calibrated probabilit" in module.SCORE_KIND


def test_does_not_reuse_ast_015_threshold() -> None:
    module = _module()
    text = SCRIPT.read_text(encoding="utf-8")
    assert "NOT the SI-009 AST 0.15" in text
    assert module.OPERATING_POINT != 0.15
    si009 = importlib.util.spec_from_file_location("si009", SI009)
    si009_mod = importlib.util.module_from_spec(si009)
    assert si009 is not None and si009.loader is not None
    si009.loader.exec_module(si009_mod)
    assert si009_mod.STRONG_SCORE == 0.15
    assert module.OPERATING_POINT == 0.50


def test_license_blocker_rejects_noncommercial() -> None:
    module = _module()
    with pytest.raises(SystemExit, match="LICENSE BLOCKER"):
        module.assert_commercial_license("cc-by-nc-4.0")
    assert module.assert_commercial_license("cc-by-4.0") == "cc-by-4.0"


def test_assess_presence_does_not_force_single_winner() -> None:
    module = _module()
    ranked = module.rank_rows(
        [
            {"label": "Guitar", "clipwise_mean": 0.62, "clipwise_max": 0.80},
            {"label": "Drum kit", "clipwise_mean": 0.55, "clipwise_max": 0.70},
            {"label": "Piano", "clipwise_mean": 0.01, "clipwise_max": 0.02},
        ]
    )
    sep = module.separation_metrics(ranked)
    assessed = module.assess_instrument_presence(ranked, sep)
    assert assessed["category_result"] == "WIN"
    assert assessed["strong_count"] == 2
    assert "Guitar" in assessed["strong_labels"]
    assert "Drum kit" in assessed["strong_labels"]


def test_assess_presence_no_win_when_flat_and_weak() -> None:
    module = _module()
    ranked = module.rank_rows(
        [
            {"label": "Guitar", "clipwise_mean": 0.065, "clipwise_max": 0.08},
            {"label": "Drum kit", "clipwise_mean": 0.009, "clipwise_max": 0.02},
            {"label": "Piano", "clipwise_mean": 0.001, "clipwise_max": 0.002},
        ]
    )
    sep = module.separation_metrics(ranked)
    assessed = module.assess_instrument_presence(ranked, sep)
    assert assessed["category_result"] == "NO WIN"


def test_engine3_final_disposition() -> None:
    module = _module()
    assert module.engine3_final("WIN") == "ENGINEERING WIN"
    assert module.engine3_final("PARTIAL") == "PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD"
    assert module.engine3_final("NO WIN") == "PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD"


def test_refuses_prior_evidence_and_ingest() -> None:
    module = _module()
    ingest = ROOT / "artifacts" / "ingest" / module._si007.LOCKED_SHA256 / "overwrite.json"
    prior = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-009-evidence" / "overwrite.json"
    with pytest.raises(SystemExit):
        module.assert_isolated_output(ingest, module._si007.LOCKED_SHA256)
    prior.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit):
        module.assert_isolated_output(prior, module._si007.LOCKED_SHA256)


def test_does_not_reopen_genre_energy_or_clap() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "genre_reopened" in text
    assert "Does not reopen genre" in text or "genre, energy" in text
    assert "measure_energy" not in text
    assert "GENRE_LABELS" not in text or "does not reopen" in text.lower()
    assert "Cnn14" in text


def test_labels_csv_has_instrument_classes() -> None:
    module = _module()
    labels = module.load_labels()
    assert "Guitar" in labels
    assert "Drum kit" in labels
    assert "Electric guitar" in labels
    assert len(labels) == 527
