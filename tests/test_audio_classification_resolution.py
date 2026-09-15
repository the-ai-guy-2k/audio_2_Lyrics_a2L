"""ACI-A2L-SI-008 isolation checks. Does not require transformers at test time."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_audio_classification_resolution.py"
SI007 = ROOT / "scripts" / "run_audio_intelligence_candidate.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_audio_classification_resolution", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_and_control_templates() -> None:
    module = _module()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module._si007.LOCKED_SHA256 in record
    assert module.EVIDENCE_DIR.name == "aci-a2l-si-008-evidence"
    assert module._si007.PROMPT_TEMPLATES["instrumentation"] == "a song featuring {label}"
    assert module._si007.PROMPT_TEMPLATES["genre_style"] == "{label} music"


def test_ensemble_templates_are_equivalent_within_category() -> None:
    module = _module()
    for templates in module.ENSEMBLE_TEMPLATES.values():
        assert len(templates) == 3
        assert all("{label}" in template for template in templates)


def test_pick_resolution_uses_top_margin_not_label() -> None:
    module = _module()
    methods = {
        "control": {"separation": {"top_margin": 0.001, "spread": 0.04}},
        "rich": {"separation": {"top_margin": 0.020, "spread": 0.03}},
        "bare": {"separation": {"top_margin": 0.019, "spread": 0.09}},
    }
    assert module.pick_resolution(methods) == "rich"


def test_assess_category_thresholds() -> None:
    module = _module()
    control = {"separation": {"top_margin": 0.0004, "spread": 0.04}}
    win = {
        "separation": {"top_margin": 0.02, "spread": 0.05},
        "text_distinctness": {"collapsed": False},
    }
    weak = {
        "separation": {"top_margin": 0.0005, "spread": 0.041},
        "text_distinctness": {"collapsed": False},
    }
    collapsed = {
        "separation": {"top_margin": 0.05, "spread": 0.08},
        "text_distinctness": {"collapsed": True},
    }
    assert module.assess_category(control, win)["category_result"] == "WIN"
    assert module.assess_category(control, weak)["category_result"] == "NO WIN"
    assert module.assess_category(control, collapsed)["assessment"] == "UNSUPPORTED"


def test_engine3_result_mapping() -> None:
    module = _module()
    assert module.engine3_result({"a": "WIN", "b": "WIN", "c": "NO WIN", "d": "NO WIN"}) == "ENGINEERING WIN"
    assert module.engine3_result({"a": "PARTIAL", "b": "PARTIAL", "c": "NO WIN", "d": "NO WIN"}) == "PARTIAL PASS"
    assert module.engine3_result({"a": "NO WIN", "b": "NO WIN", "c": "NO WIN", "d": "NO WIN"}) == "CLAP SCOPE REDUCED"


def test_refuses_si007_evidence_path() -> None:
    module = _module()
    evidence = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-007-evidence" / "overwrite.json"
    ingest = ROOT / "artifacts" / "ingest" / module._si007.LOCKED_SHA256 / "overwrite.json"
    try:
        module._si007.assert_isolated_output(ingest, module._si007.LOCKED_SHA256)
        raised = False
    except SystemExit:
        raised = True
    assert raised
    assert "aci-a2l-si-007-evidence" in str(evidence)


def test_si007_script_still_owns_energy() -> None:
    text = SI007.read_text(encoding="utf-8")
    assert "ENERGY" in text
    si008 = SCRIPT.read_text(encoding="utf-8")
    assert "Energy / Intensity was not reopened" in si008
    assert "measure_energy" not in si008
