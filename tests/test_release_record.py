"""ACI-A2L-REL-001 song release record. Do not invent missing release data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.approve import approve_reviewed_lyrics, default_approved_txt_path
from a2l.errors import ReleaseError, ReviewError
from a2l.ingest import ingest_wav
from a2l.metadata import apply_song_metadata, load_song_metadata, write_song_metadata
from a2l.release_record import (
    INCOMPLETE,
    READY,
    STATUS_AVAILABLE,
    STATUS_MISSING,
    load_or_create_release_record,
    save_release_record,
)
from a2l.review import apply_corrections, review_from_structured, save_review
from tests.test_review import _structured
from tests.wav_fixtures import write_pcm_wav


def _bind_job(monkeypatch, job: Path) -> None:
    monkeypatch.setattr("a2l.review.ingest_job_dir", lambda sha=None, artifact_root=None: job)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", lambda sha=None, artifact_root=None: job)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", lambda sha=None, artifact_root=None: job)


def _ingest(tmp_path: Path, monkeypatch, name: str = "demo.wav"):
    wav = write_pcm_wav(tmp_path / name)
    ingest = ingest_wav(wav, tmp_path / "artifacts")
    _bind_job(monkeypatch, ingest.artifact_dir)
    return ingest


def _field(record: dict, field_id: str) -> dict:
    return next(item for item in record["fields"] if item["id"] == field_id)


def _approve(ingest, tmp_path: Path):
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", ingest.job_id)
    apply_corrections(review, {1: "Hook us with that old school funk"})
    stored = load_song_metadata(ingest.job_id, job_dir=ingest.artifact_dir)
    apply_song_metadata(review, stored.get("song_title"), stored.get("artist"))
    save_review(review, sha=ingest.job_id)
    return approve_reviewed_lyrics(review, ingest.job_id, confirm=True, now="2026-09-11T00:00:00+00:00")


def test_record_reuses_title_artist_and_duration(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch, name="Jay Garrett - Stomp To.wav")
    write_song_metadata(ingest.job_id, "Stomp To", "Jay Garrett", job_dir=ingest.artifact_dir)
    record = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir, now="2026-09-11T12:00:00+00:00")
    assert _field(record, "song_title")["status"] == STATUS_AVAILABLE
    assert _field(record, "song_title")["value"] == "Stomp To"
    assert _field(record, "primary_artist")["value"] == "Jay Garrett"
    assert _field(record, "track_duration")["status"] == STATUS_AVAILABLE
    assert _field(record, "track_duration")["value"] == pytest.approx(0.1)
    assert _field(record, "master_audio")["status"] == STATUS_AVAILABLE
    assert _field(record, "approved_lyrics")["status"] == STATUS_MISSING
    assert _field(record, "songwriters")["status"] == STATUS_MISSING
    assert _field(record, "isrc")["status"] == STATUS_MISSING
    assert _field(record, "isrc")["value"] is None
    assert record["release_readiness"] == INCOMPLETE
    assert "Jay Garrett - Stomp To.wav" not in json.dumps(_field(record, "song_title"))
    path = ingest.artifact_dir / "song_release_record.json"
    assert path.is_file()


def test_missing_title_is_not_invented_from_filename(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch, name="secret-title.wav")
    record = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir)
    assert _field(record, "song_title")["status"] == STATUS_MISSING
    assert _field(record, "song_title")["value"] is None
    assert _field(record, "primary_artist")["status"] == STATUS_MISSING
    assert "secret-title" not in json.dumps(record["fields"])


def test_operator_can_save_and_reload_without_inventing_isrc(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    write_song_metadata(ingest.job_id, "Stomp To", "Jay Garrett", job_dir=ingest.artifact_dir)
    saved = save_release_record(
        ingest.job_id,
        {
            "explicit_clean": "clean",
            "songwriters": "Jay Garrett",
            "copyright_year": "2026",
            "copyright_owner": "Jay Garrett",
            "isrc": "usrc17607839",
            "featured_artists": "",
            "producers": "A Producer",
        },
        job_dir=ingest.artifact_dir,
        now="2026-09-11T12:01:00+00:00",
    )
    assert _field(saved, "explicit_clean")["value"] == "clean"
    assert _field(saved, "songwriters")["value"] == ["Jay Garrett"]
    assert _field(saved, "isrc")["value"] == "USRC17607839"
    assert _field(saved, "producers")["value"] == ["A Producer"]
    assert _field(saved, "featured_artists")["status"] == STATUS_MISSING
    assert saved["release_readiness"] == INCOMPLETE
    reloaded = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir)
    assert _field(reloaded, "isrc")["value"] == "USRC17607839"
    assert _field(reloaded, "copyright_year")["value"] == "2026"
    assert _field(reloaded, "isrc")["status"] == STATUS_AVAILABLE


def test_ready_requires_documented_fields_and_not_optional_ones(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    write_song_metadata(ingest.job_id, "Stomp To", "Jay Garrett", job_dir=ingest.artifact_dir)
    approved = _approve(ingest, tmp_path)
    before = approved["txt_path"].read_bytes()
    before_json = approved["json_path"].read_bytes()
    incomplete = save_release_record(
        ingest.job_id,
        {
            "explicit_clean": "explicit",
            "songwriters": "Jay Garrett",
            "copyright_year": "2026",
            "copyright_owner": "Jay Garrett",
        },
        job_dir=ingest.artifact_dir,
    )
    assert _field(incomplete, "approved_lyrics")["status"] == STATUS_AVAILABLE
    assert incomplete["release_readiness"] == READY
    assert _field(incomplete, "track_number")["status"] == STATUS_MISSING
    assert _field(incomplete, "disc_number")["status"] == STATUS_MISSING
    assert _field(incomplete, "composers")["status"] == STATUS_MISSING
    assert _field(incomplete, "producers")["status"] == STATUS_MISSING
    assert _field(incomplete, "publisher")["status"] == STATUS_MISSING
    assert _field(incomplete, "isrc")["status"] == STATUS_MISSING
    assert _field(incomplete, "featured_artists")["status"] == STATUS_MISSING
    blocked = save_release_record(ingest.job_id, {"songwriters": ""}, job_dir=ingest.artifact_dir)
    assert blocked["release_readiness"] == INCOMPLETE
    restored = save_release_record(ingest.job_id, {"songwriters": "Jay Garrett"}, job_dir=ingest.artifact_dir)
    assert restored["release_readiness"] == READY
    assert approved["txt_path"].read_bytes() == before
    assert approved["json_path"].read_bytes() == before_json
    assert "Hook us with that old school funk" in approved["txt_path"].read_text(encoding="utf-8")


def test_title_edit_stays_on_existing_metadata_authority(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    write_song_metadata(ingest.job_id, "Stomp", "Jay", job_dir=ingest.artifact_dir)
    save_release_record(
        ingest.job_id,
        {"song_title": "Stomp To", "primary_artist": "Jay Garrett"},
        job_dir=ingest.artifact_dir,
    )
    stored = load_song_metadata(ingest.job_id, job_dir=ingest.artifact_dir)
    record = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir)
    assert stored["song_title"] == "Stomp To"
    assert stored["artist"] == "Jay Garrett"
    assert _field(record, "song_title")["value"] == "Stomp To"
    assert _field(record, "primary_artist")["value"] == "Jay Garrett"


def test_approved_title_cannot_diverge_until_reopen(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    write_song_metadata(ingest.job_id, "Stomp To", "Jay Garrett", job_dir=ingest.artifact_dir)
    _approve(ingest, tmp_path)
    with pytest.raises(ReviewError) as exc:
        save_release_record(
            ingest.job_id,
            {"song_title": "Other Title", "primary_artist": "Jay Garrett"},
            job_dir=ingest.artifact_dir,
        )
    assert exc.value.code == "ALREADY_APPROVED"
    stored = load_song_metadata(ingest.job_id, job_dir=ingest.artifact_dir)
    assert stored["song_title"] == "Stomp To"


def test_isrc_is_not_generated_and_invalid_year_is_refused(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    record = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir)
    assert _field(record, "isrc")["value"] is None
    with pytest.raises(ReleaseError) as exc:
        save_release_record(ingest.job_id, {"copyright_year": "this-year"}, job_dir=ingest.artifact_dir)
    assert exc.value.code == "INVALID_RELEASE_FIELD"
    reloaded = load_or_create_release_record(ingest.job_id, job_dir=ingest.artifact_dir)
    assert _field(reloaded, "copyright_year")["status"] == STATUS_MISSING
    assert _field(reloaded, "isrc")["value"] is None
