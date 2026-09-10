"""ACI-A2L-006 human review tests. Do not approve lyrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.errors import ReviewError
from a2l.faster_whisper_draft import assert_not_whisper_baseline
from a2l.review import (
    LOCKED_SHA256,
    SOURCE_HUMAN,
    SOURCE_MACHINE,
    apply_corrections,
    load_saved_review,
    review_from_structured,
    save_review,
)


def _structured(tmp_path: Path) -> dict:
    return {
        "usable_as_approved_lyrics": False,
        "authority": "NON_AUTHORITATIVE_STRUCTURED_DRAFT",
        "lines": [
            {
                "index": 1,
                "kind": "machine_line",
                "start_seconds": 21.78,
                "end_seconds": 24.88,
                "preserved_text": "Hunkers with that old school funk",
                "text": "Hunkers with that old school funk",
                "status": "UNVERIFIED_MACHINE_TEXT",
                "flags": [],
                "uncertain": False,
                "section_label": None,
            },
            {
                "index": 2,
                "kind": "time_gap",
                "start_seconds": 24.88,
                "end_seconds": 31.4,
                "preserved_text": "",
                "text": "",
                "status": "REQUIRES_LATER_RESOLUTION",
                "flags": ["TIME_GAP"],
                "uncertain": True,
                "section_label": None,
            },
            {
                "index": 3,
                "kind": "machine_line",
                "start_seconds": 203.4,
                "end_seconds": 206.6,
                "preserved_text": "Thanks for watching!",
                "text": "Thanks for watching!",
                "status": "REQUIRES_LATER_RESOLUTION",
                "flags": ["WHISPER_BOILERPLATE"],
                "uncertain": True,
                "section_label": None,
            },
        ],
    }


def test_correction_persists_and_machine_text_remains(tmp_path: Path, monkeypatch) -> None:
    from a2l import review as review_mod

    monkeypatch.setattr(review_mod, "candidate_job_dir", lambda sha=LOCKED_SHA256: tmp_path / sha)
    structured_path = tmp_path / "structured_lyric_draft.json"
    structured = _structured(tmp_path)
    structured_path.write_text(json.dumps(structured), encoding="utf-8")
    review = review_from_structured(structured, structured_path, "job")
    apply_corrections(review, {1: "Hook us with that old school funk"})
    saved = save_review(review, sha="job")
    reloaded = load_saved_review(saved, sha="job")
    line = next(item for item in reloaded["lines"] if item["index"] == 1)
    assert line["machine_text"] == "Hunkers with that old school funk"
    assert line["human_text"] == "Hook us with that old school funk"
    assert line["text_source"] == SOURCE_HUMAN
    assert line["corrected"] is True
    assert reloaded["usable_as_approved_lyrics"] is False
    assert reloaded["approval_status"] == "NOT_APPROVED"


def test_uncertainty_remains_visible(tmp_path: Path) -> None:
    structured = _structured(tmp_path)
    review = review_from_structured(structured, tmp_path / "s.json", "job")
    boiler = next(item for item in review["lines"] if item["index"] == 3)
    assert boiler["uncertain"] is True
    assert "WHISPER_BOILERPLATE" in boiler["flags"]
    assert boiler["text_source"] == SOURCE_MACHINE


def test_time_gap_cannot_be_filled(tmp_path: Path) -> None:
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", "job")
    with pytest.raises(ReviewError) as exc:
        apply_corrections(review, {2: "invented lyrics"})
    assert exc.value.code == "GAP_FILL_NOT_AUTHORIZED"


def test_refuses_whisper_baseline_path() -> None:
    whisper = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "ingest"
        / LOCKED_SHA256
        / "machine_transcription"
        / "overwrite.json"
    )
    with pytest.raises(ReviewError) as exc:
        assert_not_whisper_baseline(whisper, LOCKED_SHA256)
    assert exc.value.code == "WHISPER_PATH_REFUSED"


def test_review_html_uses_paragraph_presentation() -> None:
    html = (Path(__file__).resolve().parents[1] / "a2l" / "review.html").read_text(encoding="utf-8")
    assert 'id="lyrics"' in html
    assert "class=\"lyrics\"" in html or "class='lyrics'" in html
    assert "display: inline" in html
    assert "white-space: normal" in html
    assert "contentEditable" in html or "contenteditable" in html
    assert "class=\"line\"" not in html
    assert "HUMAN TEXT<br>" not in html
