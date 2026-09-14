"""ACI-A2L-REL-003 album release readiness. Internal completeness only."""

from __future__ import annotations

import json
from pathlib import Path

from a2l.album_manifest import create_album_manifest, save_album_manifest
from a2l.album_readiness import assess_album_readiness, default_readiness_path
from a2l.release_record import INCOMPLETE, READY, save_release_record
from tests.test_album_manifest import _ingest_song
from tests.test_release_record import _approve


def _complete_song(ingest, tmp_path: Path, *, lyrics: bool = True, extra: dict | None = None) -> None:
    if lyrics:
        _approve(ingest, tmp_path)
    updates = {
        "explicit_clean": "clean",
        "songwriters": "Jay Garrett",
        "copyright_year": "2026",
        "copyright_owner": "Jay Garrett",
    }
    if extra:
        updates.update(extra)
    save_release_record(ingest.job_id, updates, job_dir=ingest.artifact_dir)


def test_complete_album_is_internally_ready_without_optional_isrc(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="ready.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    _complete_song(song, tmp_path)
    album = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=artifact_root,
        release_id="readyalbum003aaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    result = assess_album_readiness(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:00:00+00:00")
    assert result["overall_state"] == READY
    assert result["assessment_type"] == "A2L_INTERNAL_RELEASE_READINESS"
    assert result["authority"] == "A2L_INTERNAL_READINESS_ASSESSMENT"
    assert result["distributor_readiness"] is False
    assert result["not_a_release_or_distribution"] is True
    assert result["summary"] == {"tracks": 1, "ready_tracks": 1, "incomplete_tracks": 0}
    assert result["missing_album_fields"] == []
    optional_ids = {item["id"] for item in result["tracks"][0]["optional_missing_fields"]}
    assert "isrc" in optional_ids
    assert result["tracks"][0]["blocking_missing_fields"] == []
    path = default_readiness_path(album["release_id"], artifact_root)
    assert path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["overall_state"] == READY
    assert "spotify" not in json.dumps(stored).lower()
    assert (song.artifact_dir / "song_release_record.json").is_file()


def test_missing_album_identity_and_empty_tracks_are_blocking(tmp_path: Path, monkeypatch) -> None:
    _ingest_song(tmp_path, monkeypatch, name="demo.wav", frames=4410, title="Stomp To", artist="Jay")
    empty = create_album_manifest(artifact_root=tmp_path / "artifacts", release_id="emptyalbum003aaa")
    result = assess_album_readiness(empty["release_id"], artifact_root=tmp_path / "artifacts")
    assert result["overall_state"] == INCOMPLETE
    missing = {item["id"] for item in result["missing_album_fields"]}
    assert missing == {"album_title", "primary_artist", "release_type", "tracks"}
    titled = create_album_manifest(
        album_title="Demo",
        artifact_root=tmp_path / "artifacts",
        release_id="titleonly003aaa",
    )
    titled_result = assess_album_readiness(titled["release_id"], artifact_root=tmp_path / "artifacts")
    titled_missing = {item["id"] for item in titled_result["missing_album_fields"]}
    assert "album_title" not in titled_missing
    assert "primary_artist" in titled_missing
    assert "release_type" in titled_missing
    typed = create_album_manifest(
        album_title="Demo",
        primary_artist="Jay Garrett",
        artifact_root=tmp_path / "artifacts",
        release_id="notypalbum003aaa",
    )
    typed_result = assess_album_readiness(typed["release_id"], artifact_root=tmp_path / "artifacts")
    assert {item["id"] for item in typed_result["missing_album_fields"]} == {"release_type", "tracks"}
    complete_id = create_album_manifest(
        album_title="Demo",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=tmp_path / "artifacts",
        release_id="notracksalbum003",
    )
    no_tracks = assess_album_readiness(complete_id["release_id"], artifact_root=tmp_path / "artifacts")
    assert no_tracks["overall_state"] == INCOMPLETE
    assert {item["id"] for item in no_tracks["missing_album_fields"]} == {"tracks"}


def test_blocking_song_gaps_and_multiple_incomplete_tracks(tmp_path: Path, monkeypatch) -> None:
    first, artifact_root = _ingest_song(tmp_path, monkeypatch, name="a.wav", frames=4410, title="Song A", artist="Jay Garrett")
    second, artifact_root = _ingest_song(tmp_path, monkeypatch, name="b.wav", frames=8820, title="Song B", artist="Jay Garrett")
    _complete_song(first, tmp_path, lyrics=False, extra={"explicit_clean": ""})
    save_release_record(second.job_id, {"explicit_clean": "clean"}, job_dir=second.artifact_dir)
    album = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay Garrett",
        release_type="ep",
        artifact_root=artifact_root,
        release_id="gapsalbum003aaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [first.job_id, second.job_id]}, artifact_root=artifact_root)
    result = assess_album_readiness(album["release_id"], artifact_root=artifact_root)
    assert result["overall_state"] == INCOMPLETE
    assert result["summary"]["incomplete_tracks"] == 2
    first_block = {item["id"] for item in result["tracks"][0]["blocking_missing_fields"]}
    second_block = {item["id"] for item in result["tracks"][1]["blocking_missing_fields"]}
    assert "approved_lyrics" in first_block
    assert "explicit_clean" in first_block
    assert "songwriters" in second_block
    assert "copyright_owner" in second_block
    assert "approved_lyrics" in second_block
    optional_second = {item["id"] for item in result["tracks"][1]["optional_missing_fields"]}
    assert "isrc" in optional_second
    assert all(item["blocking"] is False for item in result["tracks"][1]["optional_missing_fields"])
    assert all(item["blocking"] is True for item in result["tracks"][1]["blocking_missing_fields"])


def test_reassess_uses_current_song_truth(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="ready.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    _complete_song(song, tmp_path, extra={"songwriters": ""})
    album = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay Garrett",
        release_type="single",
        artifact_root=artifact_root,
        release_id="refreshalbum003a",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    first = assess_album_readiness(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:01:00+00:00")
    assert first["overall_state"] == INCOMPLETE
    assert any(item["id"] == "songwriters" for item in first["tracks"][0]["blocking_missing_fields"])
    save_release_record(song.job_id, {"songwriters": "Jay Garrett"}, job_dir=song.artifact_dir)
    second = assess_album_readiness(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:02:00+00:00")
    assert second["overall_state"] == READY
    assert second["tracks"][0]["blocking_missing_fields"] == []
    stored = json.loads(default_readiness_path(album["release_id"], artifact_root).read_text(encoding="utf-8"))
    assert stored["overall_state"] == READY
    manifest = json.loads((artifact_root / "releases" / album["release_id"] / "album_release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["tracks"][0]["ingest_job_id"] == song.job_id
    assert "songwriters" not in json.dumps(manifest["tracks"])
