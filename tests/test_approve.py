"""ACI-A2L-008/009 approval tests. Fixture approval is isolated; locked song is Operator-approved as of ACI-A2L-009."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.approve import (
    APPROVAL_STATUS,
    STATE_APPROVED,
    STATE_DRAFT,
    STATE_REVIEWED,
    approve_reviewed_lyrics,
    clean_approved_text,
    default_approved_json_path,
    default_approved_txt_path,
    locked_song_is_unapproved,
    lyric_display_state,
)
from a2l.errors import ApprovalError, ReviewError
from a2l.pipeline import LOCKED_SHA256
from a2l.review import (
    apply_corrections,
    default_review_path,
    load_saved_review,
    review_from_structured,
    save_review,
)
from tests.test_review import _structured


FIXTURE_SHA = "aci-a2l-008-fixture"


def _patch_job(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("a2l.review.ingest_job_dir", lambda sha=LOCKED_SHA256: tmp_path / sha)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", lambda sha=LOCKED_SHA256: tmp_path / sha)


def test_new_review_is_draft_until_saved(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    assert review["lyric_state"] == STATE_DRAFT
    assert review["approval_status"] == "NOT_APPROVED"
    assert review["usable_as_approved_lyrics"] is False
    assert lyric_display_state(review, FIXTURE_SHA) == STATE_DRAFT


def test_save_does_not_approve(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    apply_corrections(review, {1: "Hook us with that old school funk"})
    saved = save_review(review, sha=FIXTURE_SHA)
    reloaded = load_saved_review(saved, sha=FIXTURE_SHA)
    assert reloaded["lyric_state"] == STATE_REVIEWED
    assert reloaded["approval_status"] == "NOT_APPROVED"
    assert reloaded["usable_as_approved_lyrics"] is False
    assert lyric_display_state(reloaded, FIXTURE_SHA) == STATE_REVIEWED
    assert not default_approved_txt_path(FIXTURE_SHA).exists()
    assert not default_approved_json_path(FIXTURE_SHA).exists()


def test_approval_requires_explicit_confirm(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    save_review(review, sha=FIXTURE_SHA)
    with pytest.raises(ApprovalError) as exc:
        approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=False)
    assert exc.value.code == "APPROVAL_NOT_EXPLICIT"
    assert lyric_display_state(review, FIXTURE_SHA) == STATE_REVIEWED
    assert not default_approved_txt_path(FIXTURE_SHA).exists()


def test_explicit_approval_creates_clean_artifacts(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    apply_corrections(review, {1: "Hook us with that old school funk"})
    save_review(review, sha=FIXTURE_SHA)
    result = approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-10T00:00:00+00:00")
    assert result["lyric_state"] == STATE_APPROVED
    txt = result["txt_path"]
    js = result["json_path"]
    assert txt.is_file()
    assert js.is_file()
    body = txt.read_text(encoding="utf-8")
    assert "Hook us with that old school funk" in body
    assert "Thanks for watching!" in body
    assert "00:" not in body
    assert "UNCERTAIN" not in body
    assert "MACHINE" not in body
    assert "flags=" not in body
    payload = json.loads(js.read_text(encoding="utf-8"))
    assert payload["approval_status"] == APPROVAL_STATUS
    assert payload["usable_as_approved_lyrics"] is True
    assert payload["source_sha256"] == FIXTURE_SHA
    assert payload["transcription_engine"] == "faster-whisper"
    assert payload["transcription_model"] == "large-v3"
    assert payload["approval_event"]["method"] == "EXPLICIT_CONFIRM"
    assert payload["approval_event"]["automatic"] is False
    assert payload["approved_lyric_text"] == body
    reloaded = load_saved_review(sha=FIXTURE_SHA)
    assert reloaded["approval_status"] == "APPROVED"
    assert reloaded["lyric_state"] == STATE_APPROVED
    line = next(item for item in reloaded["lines"] if item["index"] == 1)
    assert line["machine_text"] == "Hunkers with that old school funk"
    assert line["human_text"] == "Hook us with that old school funk"
    assert lyric_display_state(reloaded, FIXTURE_SHA) == STATE_APPROVED


def test_save_after_approval_is_refused(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    save_review(review, sha=FIXTURE_SHA)
    approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True)
    with pytest.raises(ReviewError) as exc:
        apply_corrections(review, {1: "changed after approval"})
    assert exc.value.code == "ALREADY_APPROVED"


def test_clean_text_omits_time_gaps_and_clutter() -> None:
    review = {
        "lines": [
            {"kind": "machine_line", "human_text": "  First line  "},
            {"kind": "time_gap", "human_text": ""},
            {"kind": "machine_line", "human_text": "Second line"},
        ]
    }
    text = clean_approved_text(review)
    assert text == "First line\nSecond line\n"


def test_locked_song_is_operator_approved() -> None:
    assert locked_song_is_unapproved() is False
    txt = default_approved_txt_path(LOCKED_SHA256)
    js = default_approved_json_path(LOCKED_SHA256)
    assert txt.is_file()
    assert js.is_file()
    body = txt.read_text(encoding="utf-8")
    assert "00:" not in body
    assert "UNCERTAIN" not in body
    assert "flags=" not in body
    payload = json.loads(js.read_text(encoding="utf-8"))
    assert payload["approval_status"] == APPROVAL_STATUS
    assert payload["usable_as_approved_lyrics"] is True
    assert payload["source_sha256"] == LOCKED_SHA256
    assert payload["transcription_engine"] == "faster-whisper"
    assert payload["approval_event"]["method"] == "EXPLICIT_CONFIRM"
    assert payload["approval_event"]["automatic"] is False
    assert payload["approved_lyric_text"] == body
    review = json.loads(default_review_path(LOCKED_SHA256).read_text(encoding="utf-8"))
    assert lyric_display_state(review, LOCKED_SHA256) == STATE_APPROVED


def test_review_html_exposes_explicit_approval() -> None:
    html = (Path(__file__).resolve().parents[1] / "a2l" / "review.html").read_text(encoding="utf-8")
    assert 'id="lyric-state"' in html
    assert "Mark lyrics APPROVED" in html
    assert "/api/approve" in html
    assert "confirm: true" in html
    assert "Save does not approve" in html
    assert "DRAFT" in html and "REVIEWED" in html and "APPROVED" in html
