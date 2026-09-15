"""ACI-A2L-SI-007 isolation checks. Does not require transformers at test time."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_audio_intelligence_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_audio_intelligence_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_checkpoint_and_license() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert module.ENGINE_NAME == "transformers ClapModel"
    assert module.CHECKPOINT == "laion/larger_clap_music"
    assert module.LICENSE_DECLARED == "apache-2.0"
    assert "calibrated probability" in module.SCORE_KIND
    assert module.CANDIDATE_DIR_NAME == "clap-audio-intelligence"
    assert module.EVIDENCE_DIR.name == "aci-a2l-si-007-evidence"


def test_vocabulary_matches_aci_labels() -> None:
    module = _candidate()
    assert module.VOCABULARIES["genre_style"] == [
        "country",
        "country rock",
        "southern rock",
        "rock",
        "blues",
        "funk",
        "pop",
        "americana",
        "roots rock",
    ]
    assert "synthesizer" in module.VOCABULARIES["instrumentation"]
    assert "percussion" in module.VOCABULARIES["instrumentation"]
    assert "vocals present" in module.VOCABULARIES["vocal_character"]
    assert "predominantly instrumental" in module.VOCABULARIES["vocal_character"]
    assert "mixed acoustic/electric" in module.VOCABULARIES["acoustic_electronic"]
    assert "mood_character" not in module.VOCABULARIES
    assert module.prompt_for("genre_style", "country rock") == "country rock music"


def test_rank_category_orders_by_cosine_not_softmax_label() -> None:
    module = _candidate()
    audio = [1.0, 0.0]
    items = [
        {"label": "rock", "display": "Rock", "prompt": "rock music", "embed": [0.2, 0.8]},
        {"label": "country rock", "display": "Country Rock", "prompt": "country rock music", "embed": [1.0, 0.0]},
    ]
    ranked = module.rank_category(audio, items, logit_scale=1.0)
    assert ranked[0]["label"] == "country rock"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["score_kind"] == "cosine_similarity"
    assert "softmax_within_category" in ranked[0]


def test_clap_logit_scale_prefers_audio_parameter() -> None:
    module = _candidate()

    class _Param:
        def __init__(self, value: float) -> None:
            self._value = value

        def exp(self):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def item(self):
            return self._value

    model = SimpleNamespace(logit_scale_a=_Param(2.5), logit_scale=_Param(9.0))
    assert module.clap_logit_scale(model) == 2.5
    with pytest.raises(SystemExit, match="logit scale"):
        module.clap_logit_scale(SimpleNamespace())


def test_energy_label_thresholds() -> None:
    module = _candidate()
    assert module.energy_label_from_rms(0.20) == "HIGH ENERGY"
    assert module.energy_label_from_rms(0.10) == "MEDIUM ENERGY"
    assert module.energy_label_from_rms(0.01) == "LOW ENERGY"


def test_chunk_ranges_cover_long_audio() -> None:
    module = _candidate()
    ranges = module.chunk_ranges(48000 * 25, 48000, chunk_seconds=10.0, hop_seconds=10.0)
    assert ranges[0] == (0, 480000)
    assert ranges[-1][1] == 48000 * 25
    assert len(ranges) == 3


def test_license_blocker_rejects_noncommercial() -> None:
    module = _candidate()
    with pytest.raises(SystemExit, match="LICENSE BLOCKER"):
        module.assert_commercial_license("cc-by-nc-4.0")
    assert module.assert_commercial_license("apache-2.0") == "apache-2.0"


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
        / "audio_intelligence_readable.txt"
    )
    module.assert_isolated_output(candidate, module.LOCKED_SHA256)


def test_processor_supports_audios_or_audio_kwargs() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "def process_audio" in text
    assert "audios=chunk" in text
    assert "audio=chunk" in text


def test_text_method_records_eos_pooling() -> None:
    module = _candidate()
    assert "EOS-token" in module.METHOD


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-clap-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
