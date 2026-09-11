"""ACI-A2L-013 derived approved-lyric export formatting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.approve import approve_reviewed_lyrics, default_approved_json_path, default_approved_txt_path
from a2l.errors import ExportError
from a2l.export import (
    DEFAULT_FORMAT,
    FORMAT_PLAIN,
    FORMAT_STANDARD,
    FORMAT_STRUCTURED,
    default_exports_dir,
    format_approved_export,
)
from a2l.pipeline import LOCKED_SHA256
from a2l.review import apply_corrections, review_from_structured, save_review as persist_review
from tests.test_approve import FIXTURE_SHA, _patch_job
from tests.test_review import _structured


def _approve(tmp_path: Path, monkeypatch, extra_review=None):
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    apply_corrections(review, {1: "Hook us with that old school funk"})
    if extra_review:
        extra_review(review)
    persist_review(review, sha=FIXTURE_SHA)
    return approve_reviewed_lyrics(review, FIXTURE_SHA, confirm=True, now="2026-09-11T00:00:00+00:00")


def test_unapproved_lyrics_cannot_export(tmp_path: Path, monkeypatch) -> None:
    _patch_job(monkeypatch, tmp_path)
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", FIXTURE_SHA)
    persist_review(review, sha=FIXTURE_SHA)
    with pytest.raises(ExportError) as exc:
        format_approved_export(FIXTURE_SHA, DEFAULT_FORMAT)
    assert exc.value.code == "NOT_APPROVED"


def test_default_format_is_standard_lyric_sheet(tmp_path: Path, monkeypatch) -> None:
    result = _approve(tmp_path, monkeypatch)
    canonical = result["txt_path"].read_text(encoding="utf-8")
    export = format_approved_export(FIXTURE_SHA)
    assert export.format_id == FORMAT_STANDARD
    assert export.label == "STANDARD LYRIC SHEET"
    assert export.text == canonical
    assert "Hook us with that old school funk" in export.text
    assert "Verse" not in export.text
    assert "Chorus" not in export.text


def test_plain_text_matches_canonical_words(tmp_path: Path, monkeypatch) -> None:
    result = _approve(tmp_path, monkeypatch)
    canonical = result["txt_path"].read_text(encoding="utf-8")
    before_txt = canonical
    before_json = result["json_path"].read_bytes()
    export = format_approved_export(FIXTURE_SHA, FORMAT_PLAIN)
    assert export.text == canonical
    assert result["txt_path"].read_text(encoding="utf-8") == before_txt
    assert result["json_path"].read_bytes() == before_json


def test_standard_sheet_shows_existing_metadata_only(tmp_path: Path, monkeypatch) -> None:
    result = _approve(tmp_path, monkeypatch)
    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    payload["song_title"] = "Stomp"
    payload["artist"] = "Jay"
    result["json_path"].write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    canonical = result["txt_path"].read_text(encoding="utf-8")
    export = format_approved_export(FIXTURE_SHA, FORMAT_STANDARD)
    assert export.text.startswith("Stomp\nJay\n\n")
    assert export.text.endswith(canonical)
    assert export.text[len("Stomp\nJay\n\n") :] == canonical


def test_structured_does_not_invent_sections(tmp_path: Path, monkeypatch) -> None:
    result = _approve(tmp_path, monkeypatch)
    canonical = result["txt_path"].read_text(encoding="utf-8")
    export = format_approved_export(FIXTURE_SHA, FORMAT_STRUCTURED)
    assert export.text == canonical
    assert "Verse" not in export.text


def test_structured_preserves_existing_section_labels(tmp_path: Path, monkeypatch) -> None:
    def label(review):
        for line in review["lines"]:
            if line.get("index") == 1:
                line["section_label"] = "Chorus"

    result = _approve(tmp_path, monkeypatch, extra_review=label)
    canonical = result["txt_path"].read_text(encoding="utf-8")
    export = format_approved_export(FIXTURE_SHA, FORMAT_STRUCTURED)
    assert export.text.startswith("Chorus\n\nHook us with that old school funk\n")
    assert "Hook us with that old school funk" in canonical
    body_lines = [line for line in export.text.splitlines() if line and line != "Chorus"]
    assert body_lines == [line for line in canonical.splitlines() if line]


def test_unknown_format_is_refused(tmp_path: Path, monkeypatch) -> None:
    _approve(tmp_path, monkeypatch)
    with pytest.raises(ExportError) as exc:
        format_approved_export(FIXTURE_SHA, "pdf")
    assert exc.value.code == "UNKNOWN_FORMAT"


def test_derived_exports_do_not_replace_canonical_artifacts(tmp_path: Path, monkeypatch) -> None:
    result = _approve(tmp_path, monkeypatch)
    exports = default_exports_dir(FIXTURE_SHA)
    assert (exports / "lyric-sheet.txt").is_file()
    assert (exports / "export_provenance.json").is_file()
    provenance = json.loads((exports / "export_provenance.json").read_text(encoding="utf-8"))
    assert provenance["usable_as_approved_lyrics"] is False
    assert provenance["authority"] == "DERIVED_EXPORT_PRESENTATION"
    assert result["txt_path"].name == "approved_lyrics.txt"
    assert result["json_path"].name == "approved_lyrics.json"
    assert result["txt_path"].parent.name == "approved_lyrics"
    assert exports != result["txt_path"]


def test_existing_approved_artifact_formats_without_rewrite() -> None:
    txt = default_approved_txt_path(LOCKED_SHA256)
    js = default_approved_json_path(LOCKED_SHA256)
    before_txt = txt.read_bytes()
    before_json = js.read_bytes()
    canonical = txt.read_text(encoding="utf-8")
    export = format_approved_export(LOCKED_SHA256)
    assert export.format_id == FORMAT_STANDARD
    assert export.text == canonical
    assert txt.read_bytes() == before_txt
    assert js.read_bytes() == before_json
    payload = json.loads(js.read_text(encoding="utf-8"))
    assert payload["transcription_engine"] == "faster-whisper"
    assert payload["usable_as_approved_lyrics"] is True
    plain = format_approved_export(LOCKED_SHA256, FORMAT_PLAIN)
    assert plain.text == canonical
    structured = format_approved_export(LOCKED_SHA256, FORMAT_STRUCTURED)
    assert structured.text == canonical
    assert txt.read_bytes() == before_txt
    assert js.read_bytes() == before_json
