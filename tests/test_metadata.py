"""ACI-A2L-014 operator-provided song title and artist."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.approve import approve_reviewed_lyrics, reopen_approved_lyrics
from a2l.errors import ReviewError
from a2l.export import FORMAT_PLAIN, FORMAT_STANDARD, FORMAT_STRUCTURED, format_approved_export
from a2l.metadata import (
    apply_song_metadata,
    load_song_metadata,
    normalize_song_metadata,
    write_song_metadata,
)
from a2l.review import apply_corrections, review_from_structured, save_review
from tests.test_approve import FIXTURE_SHA, _patch_job
from tests.test_review import _structured


def _review(tmp_path: Path, monkeypatch):
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    apply_corrections(review, {1: "Hook us with that old school funk"})
    return review


def test_normalize_does_not_invent_or_use_filename() -> None:
    assert normalize_song_metadata(None, None) == {"song_title": None, "artist": None}
    assert normalize_song_metadata("", "  ") == {"song_title": None, "artist": None}
    assert normalize_song_metadata("  Stomp  ", " Jay ") == {"song_title": "Stomp", "artist": "Jay"}
    assert "demo.wav" not in json.dumps(normalize_song_metadata(None, None))


def test_filename_is_not_written_as_title(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    path = write_song_metadata(FIXTURE_SHA, None, None, job_dir=tmp_path / FIXTURE_SHA)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["song_title"] is None
    assert payload["artist"] is None
    assert payload["source_filename_used_as_title"] is False
    assert payload["inferred_from_filename"] is False
    assert "demo.wav" not in path.read_text(encoding="utf-8")


def test_apply_and_save_persists_independently_of_lyrics(tmp_path: Path, monkeypatch) -> None:
    review = _review(tmp_path, monkeypatch)
    apply_song_metadata(review, "Stomp", "Jay")
    save_review(review, sha=FIXTURE_SHA)
    stored = load_song_metadata(FIXTURE_SHA, job_dir=tmp_path / FIXTURE_SHA)
    assert stored["song_title"] == "Stomp"
    assert stored["artist"] == "Jay"
    assert review["lines"][0]["human_text"] == "Hook us with that old school funk"


def test_approval_preserves_metadata_without_changing_lyric_words(tmp_path: Path, monkeypatch) -> None:
    review = _review(tmp_path, monkeypatch)
    apply_song_metadata(review, "Stomp", None)
    save_review(review, sha=FIXTURE_SHA)
    approved = approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-11T12:00:00+00:00")
    payload = json.loads(approved["json_path"].read_text(encoding="utf-8"))
    canonical = approved["txt_path"].read_text(encoding="utf-8")
    assert payload["song_title"] == "Stomp"
    assert payload["artist"] is None
    assert "Stomp" not in canonical
    assert "Hook us with that old school funk" in canonical
    sheet = format_approved_export(FIXTURE_SHA)
    assert sheet.format_id == FORMAT_STANDARD
    assert sheet.text.startswith("Stomp\n\n")
    assert sheet.text.endswith(canonical)
    plain = format_approved_export(FIXTURE_SHA, FORMAT_PLAIN)
    assert plain.text == canonical
    structured = format_approved_export(FIXTURE_SHA, FORMAT_STRUCTURED)
    assert structured.text == canonical


def test_approved_metadata_cannot_change_until_reopen(tmp_path: Path, monkeypatch) -> None:
    review = _review(tmp_path, monkeypatch)
    apply_song_metadata(review, "Stomp", "Jay")
    save_review(review, sha=FIXTURE_SHA)
    approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-11T12:00:00+00:00")
    with pytest.raises(ReviewError) as exc:
        apply_song_metadata(review, "Other", "Someone")
    assert exc.value.code == "ALREADY_APPROVED"
    reopen_approved_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-11T13:00:00+00:00")
    apply_song_metadata(review, "Corrected Title", "Corrected Artist")
    save_review(review, sha=FIXTURE_SHA)
    second = approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-11T14:00:00+00:00")
    payload = json.loads(second["json_path"].read_text(encoding="utf-8"))
    assert payload["song_title"] == "Corrected Title"
    assert payload["artist"] == "Corrected Artist"
    assert payload["approval_event"]["revision"] == 2
    canonical = second["txt_path"].read_text(encoding="utf-8")
    assert "Corrected Title" not in canonical
    sheet = format_approved_export(FIXTURE_SHA)
    assert sheet.text.startswith("Corrected Title\nCorrected Artist\n\n")
    assert sheet.text.endswith(canonical)
