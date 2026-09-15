"""ACI-A2L-SI-006 isolation checks. Stdlib only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_lyric_intelligence_candidate.py"


def _candidate():
    spec = importlib.util.spec_from_file_location("run_lyric_intelligence_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_locked_sha_and_method() -> None:
    module = _candidate()
    record = (ROOT / "docs" / "nebula" / "FIXED_TEST_SONG.md").read_text(encoding="utf-8")
    assert module.LOCKED_SHA256 in record
    assert module.ENGINE_NAME == "in-repo deterministic lyric NLP"
    assert module.CANDIDATE_DIR_NAME == "lyric-intelligence"
    assert "stdlib" in module.METHOD


def test_repeated_phrase_ranks_as_theme() -> None:
    module = _candidate()
    text = "Play something we can stomp to\nPlay something we can stomp to\nQuiet night alone\n"
    result = module.analyze_lyrics(text)
    assert result["themes"][0]["phrase"] == "play something we can stomp to"
    assert result["themes"][0]["count"] == 2
    keywords = {item["keyword"] for item in result["keywords"]}
    assert "stomp" in keywords
    assert "can" not in keywords
    assert "the" not in keywords


def test_synopsis_uses_only_source_phrases() -> None:
    module = _candidate()
    text = "Mr. Guitar Man\nPlay something we can stomp to\nPlay something we can stomp to\n"
    result = module.analyze_lyrics(text)
    synopsis = result["synopsis"]["text"].lower()
    assert "mr. guitar man" in synopsis
    assert "stomp" in synopsis
    assert "biography" not in synopsis


def test_emotion_overlap_is_lexical() -> None:
    module = _candidate()
    text = "We dance and stomp and groove and funk\nWe dance and stomp and groove and funk\n"
    result = module.analyze_lyrics(text)
    assert result["emotional_character"]["label"] in {"energetic", "celebratory"}
    assert result["emotional_character"]["overlap_count"] > 0


def test_rejects_unapproved_json(tmp_path: Path) -> None:
    module = _candidate()
    (tmp_path / "approved_lyrics.txt").write_text("hello\n", encoding="utf-8")
    payload = {
        "approval_status": "REVIEWED",
        "usable_as_approved_lyrics": False,
        "authority": "AUTHORITATIVE_APPROVED_LYRICS",
        "approved_lyric_text": "hello\n",
        "source_sha256": module.LOCKED_SHA256,
    }
    (tmp_path / "approved_lyrics.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SystemExit, match="not APPROVED"):
        module.load_approved_pair(tmp_path)


def test_refuses_ingest_output_path() -> None:
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
        / "lyric_intelligence_readable.txt"
    )
    module.assert_isolated_output(candidate, module.LOCKED_SHA256)


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    module = _candidate()
    path = tmp_path / "sample.bin"
    path.write_bytes(b"a2l-lyric-intelligence-isolation")
    assert module.sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
