"""ACI-A2L-SI-009 isolation checks. Does not require transformers at test time."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_instrumentation_genre_candidate.py"
SI007 = ROOT / "scripts" / "run_audio_intelligence_candidate.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_instrumentation_genre_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_checkpoint_and_license() -> None:
    module = _module()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module._si007.LOCKED_SHA256 in record
    assert module.ENGINE_NAME == "transformers ASTForAudioClassification"
    assert module.CHECKPOINT == "MIT/ast-finetuned-audioset-10-10-0.4593"
    assert module.CHECKPOINT_REVISION == "f826b80d28226b62986cc218e5cec390b1096902"
    assert module.LICENSE_DECLARED == "bsd-3-clause"
    assert "bsd-3-clause" in module.ALLOWED_LICENSES
    assert module.CANDIDATE_DIR_NAME == "ast-instrumentation-genre"
    assert module.EVIDENCE_DIR.name == "aci-a2l-si-009-evidence"
    assert "calibrated probability" in module.SCORE_KIND


def test_native_taxonomy_is_not_si007_clap_vocabulary() -> None:
    module = _module()
    assert "Electric guitar" in module.INSTRUMENT_LABELS
    assert "Drum kit" in module.INSTRUMENT_LABELS
    assert "Country" in module.GENRE_LABELS
    assert "Rock music" in module.GENRE_LABELS
    assert "Funk" in module.GENRE_LABELS
    assert "country rock" not in {label.lower() for label in module.GENRE_LABELS}
    assert "americana" not in {label.lower() for label in module.GENRE_LABELS}
    assert "Music" not in module.INSTRUMENT_LABELS
    assert "Music" not in module.GENRE_LABELS
    assert "electric guitar" not in module.INSTRUMENT_LABELS


def test_license_blocker_rejects_noncommercial() -> None:
    module = _module()
    with pytest.raises(SystemExit, match="LICENSE BLOCKER"):
        module.assert_commercial_license("cc-by-nc-4.0")
    with pytest.raises(SystemExit, match="LICENSE BLOCKER"):
        module.assert_commercial_license("agpl-3.0")
    assert module.assert_commercial_license("bsd-3-clause") == "bsd-3-clause"
    text = SCRIPT.read_text(encoding="utf-8")
    assert "not_inferred_from_transformers_license" in text
    assert "Does not continue CLAP" in module.__doc__


def test_assess_category_thresholds() -> None:
    module = _module()
    win_margin = module.assess_category(
        {
            "top_margin": 0.12,
            "spread": 0.20,
            "strong_count": 1,
            "weak_count": 10,
            "label_count": 12,
        }
    )
    win_cluster = module.assess_category(
        {
            "top_margin": 0.01,
            "spread": 0.40,
            "strong_count": 3,
            "weak_count": 20,
            "label_count": 30,
        }
    )
    partial = module.assess_category(
        {
            "top_margin": 0.03,
            "spread": 0.04,
            "strong_count": 0,
            "weak_count": 10,
            "label_count": 12,
        }
    )
    none = module.assess_category(
        {
            "top_margin": 0.004,
            "spread": 0.02,
            "strong_count": 0,
            "weak_count": 10,
            "label_count": 12,
        }
    )
    assert win_margin["category_result"] == "WIN"
    assert win_cluster["category_result"] == "WIN"
    assert partial["category_result"] == "PARTIAL"
    assert none["category_result"] == "NO WIN"


def test_engine3_requires_both_category_wins() -> None:
    module = _module()
    assert module.engine3_result("WIN", "WIN") == "ENGINEERING WIN"
    assert module.engine3_result("WIN", "NO WIN") == "PARTIAL PASS"
    assert module.engine3_result("NO WIN", "NO WIN") == "PARTIAL PASS"
    assert module.engine3_result("PARTIAL", "WIN") == "PARTIAL PASS"


def test_group_scores_use_max_of_native_members() -> None:
    module = _module()
    ranked = module.rank_scores(
        [
            {"label": "Electric guitar", "sigmoid_score": 0.40},
            {"label": "Acoustic guitar", "sigmoid_score": 0.10},
            {"label": "Drum kit", "sigmoid_score": 0.55},
            {"label": "Piano", "sigmoid_score": 0.02},
        ]
    )
    grouped = {row["group"]: row for row in module.group_scores(ranked)}
    assert grouped["guitar_family"]["sigmoid_score"] == 0.40
    assert grouped["drums_percussion"]["sigmoid_score"] == 0.55
    assert grouped["keyboard_piano_organ"]["sigmoid_score"] == 0.02


def test_refuses_ingest_and_prior_evidence_paths() -> None:
    module = _module()
    ingest = ROOT / "artifacts" / "ingest" / module._si007.LOCKED_SHA256 / "overwrite.json"
    prior = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-008-evidence" / "overwrite.json"
    with pytest.raises(SystemExit):
        module.assert_isolated_output(ingest, module._si007.LOCKED_SHA256)
    prior.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit):
        module.assert_isolated_output(prior, module._si007.LOCKED_SHA256)


def test_candidate_output_dir_is_isolated() -> None:
    module = _module()
    candidate = (
        ROOT
        / "artifacts"
        / "candidates"
        / module.CANDIDATE_DIR_NAME
        / module._si007.LOCKED_SHA256
        / "instrumentation_genre_readable.txt"
    )
    module.assert_isolated_output(candidate, module._si007.LOCKED_SHA256)


def test_does_not_reopen_clap_energy_or_si007_vocabularies() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    si007 = SI007.read_text(encoding="utf-8")
    assert "measure_energy" not in text
    assert "ENERGY_HIGH_RMS" not in text
    assert "Does not continue CLAP" in text
    assert "a song featuring {label}" not in text
    assert "ENERGY" in si007
