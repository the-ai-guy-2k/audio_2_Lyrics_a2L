"""ACI-A2L-REL-002 album release manifest. Do not invent missing release data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.album_manifest import (
    add_album_track,
    create_album_manifest,
    default_manifest_path,
    load_album_manifest,
    remove_album_track,
    save_album_manifest,
)
from a2l.errors import ReleaseError
from a2l.ingest import ingest_wav
from a2l.metadata import write_song_metadata
from a2l.release_record import INCOMPLETE, READY, save_release_record
from tests.test_release_record import _approve
from tests.wav_fixtures import write_pcm_wav


def _bind_root(monkeypatch, artifact_root: Path) -> None:
    def job_dir(sha=None, artifact_root=artifact_root):
        return artifact_root / "ingest" / sha

    monkeypatch.setattr("a2l.review.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", job_dir)


def _ingest_song(tmp_path: Path, monkeypatch, *, name: str, frames: int, title=None, artist=None):
    artifact_root = tmp_path / "artifacts"
    wav = write_pcm_wav(tmp_path / name, frame_count=frames)
    ingest = ingest_wav(wav, artifact_root)
    _bind_root(monkeypatch, artifact_root)
    if title is not None or artist is not None:
        write_song_metadata(ingest.job_id, title, artist, job_dir=ingest.artifact_dir)
    return ingest, artifact_root


def test_album_fields_persist_and_are_not_inferred(tmp_path: Path, monkeypatch) -> None:
    _song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="secret-album.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    created = create_album_manifest(artifact_root=artifact_root, now="2026-09-11T20:00:00+00:00", release_id="albumrel002aaa")
    assert created["album_title"] is None
    assert created["primary_artist"] is None
    assert created["release_type"] is None
    assert created["tracks"] == []
    assert created["summary"] == {"tracks": 0, "song_records_ready": 0, "song_records_incomplete": 0}
    assert created["album_ready_determination"] is False
    assert "album_ready" not in created
    path = default_manifest_path(created["release_id"], artifact_root)
    assert path.is_file()
    assert "secret-album" not in path.as_posix()
    saved = save_album_manifest(
        created["release_id"],
        {"album_title": "Stomp Collection", "primary_artist": "Jay Garrett", "release_type": "EP"},
        artifact_root=artifact_root,
        now="2026-09-11T20:01:00+00:00",
    )
    assert saved["album_title"] == "Stomp Collection"
    assert saved["primary_artist"] == "Jay Garrett"
    assert saved["release_type"] == "ep"
    reloaded = load_album_manifest(created["release_id"], artifact_root=artifact_root)
    assert reloaded["album_title"] == "Stomp Collection"
    assert reloaded["primary_artist"] == "Jay Garrett"
    assert reloaded["release_type"] == "ep"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["album_title"] == "Stomp Collection"
    assert stored["tracks"] == []
    assert stored["album_ready_determination"] is False
    assert stored["provenance"]["album_title"] == "OPERATOR_ENTERED"


def test_unsafe_album_title_is_not_used_as_path(tmp_path: Path, monkeypatch) -> None:
    _ingest_song(tmp_path, monkeypatch, name="a.wav", frames=4410)
    created = create_album_manifest(
        album_title="A/B: Hits?",
        primary_artist="Jay",
        release_type="album",
        artifact_root=tmp_path / "artifacts",
        release_id="safereleaseid001",
    )
    path = default_manifest_path(created["release_id"], tmp_path / "artifacts")
    assert path.parent.name == "safereleaseid001"
    assert "A" not in path.parent.name or path.parent.name == "safereleaseid001"
    assert "Hits" not in path.as_posix()
    assert created["album_title"] == "A/B: Hits?"


def test_track_membership_order_and_remove_do_not_delete_songs(tmp_path: Path, monkeypatch) -> None:
    first, artifact_root = _ingest_song(tmp_path, monkeypatch, name="b-second.wav", frames=4410, title="Song B", artist="Jay")
    second, artifact_root = _ingest_song(tmp_path, monkeypatch, name="a-first.wav", frames=8820, title="Song A", artist="Jay")
    created = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay",
        release_type="album",
        artifact_root=artifact_root,
        release_id="orderrelease001",
        now="2026-09-11T20:02:00+00:00",
    )
    added = save_album_manifest(
        created["release_id"],
        {"track_ids": [second.job_id, first.job_id]},
        artifact_root=artifact_root,
        now="2026-09-11T20:03:00+00:00",
    )
    assert [item["song_title"] for item in added["tracks"]] == ["Song A", "Song B"]
    assert [item["ingest_job_id"] for item in added["tracks"]] == [second.job_id, first.job_id]
    assert added["tracks"][0]["position"] == 1
    assert added["tracks"][1]["position"] == 2
    reordered = save_album_manifest(
        created["release_id"],
        {"track_ids": [first.job_id, second.job_id]},
        artifact_root=artifact_root,
        now="2026-09-11T20:04:00+00:00",
    )
    assert [item["ingest_job_id"] for item in reordered["tracks"]] == [first.job_id, second.job_id]
    reloaded = load_album_manifest(created["release_id"], artifact_root=artifact_root)
    assert [item["ingest_job_id"] for item in reloaded["tracks"]] == [first.job_id, second.job_id]
    stored = json.loads(default_manifest_path(created["release_id"], artifact_root).read_text(encoding="utf-8"))
    assert "song_title" not in json.dumps(stored["tracks"])
    assert "release_readiness" not in json.dumps(stored["tracks"])
    removed = remove_album_track(created["release_id"], first.job_id, artifact_root=artifact_root)
    assert [item["ingest_job_id"] for item in removed["tracks"]] == [second.job_id]
    assert (first.artifact_dir / "ingest_manifest.json").is_file()
    assert first.artifact_dir.is_dir()
    with pytest.raises(ReleaseError) as exc:
        add_album_track(created["release_id"], second.job_id, artifact_root=artifact_root)
    assert exc.value.code == "TRACK_ALREADY_ON_ALBUM"


def test_live_song_release_truth_and_missing_fields(tmp_path: Path, monkeypatch) -> None:
    incomplete, artifact_root = _ingest_song(tmp_path, monkeypatch, name="incomplete.wav", frames=4410, title="Song B", artist="Jay")
    ready_song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="ready.wav", frames=8820, title="Song A", artist="Jay Garrett")
    _approve(ready_song, tmp_path)
    save_release_record(
        ready_song.job_id,
        {
            "explicit_clean": "clean",
            "songwriters": "Jay Garrett",
            "copyright_year": "2026",
            "copyright_owner": "Jay Garrett",
        },
        job_dir=ready_song.artifact_dir,
    )
    album = create_album_manifest(album_title="Demo", primary_artist="Jay", release_type="album", artifact_root=artifact_root, release_id="truthrelease001")
    view = save_album_manifest(
        album["release_id"],
        {"track_ids": [ready_song.job_id, incomplete.job_id]},
        artifact_root=artifact_root,
    )
    assert view["tracks"][0]["release_readiness"] == READY
    assert view["tracks"][0]["approved_lyrics_status"] == "AVAILABLE"
    assert view["tracks"][1]["release_readiness"] == INCOMPLETE
    assert view["tracks"][1]["approved_lyrics_status"] == "MISSING"
    missing_labels = {item["label"] for item in view["tracks"][1]["missing_fields"]}
    assert "Songwriter(s)" in missing_labels
    assert "Copyright Owner" in missing_labels
    assert "ISRC" in missing_labels
    assert view["summary"]["tracks"] == 2
    assert view["summary"]["song_records_ready"] == 1
    assert view["summary"]["song_records_incomplete"] == 1
    assert view["album_ready_determination"] is False
    isrc_before = next(item for item in view["tracks"][1]["missing_fields"] if item["id"] == "isrc")
    assert isrc_before["status"] == "MISSING"
    save_release_record(incomplete.job_id, {"isrc": "USRC17607839", "songwriters": "Jay Garrett"}, job_dir=incomplete.artifact_dir)
    refreshed = load_album_manifest(album["release_id"], artifact_root=artifact_root)
    refreshed_missing = {item["id"] for item in refreshed["tracks"][1]["missing_fields"]}
    assert "isrc" not in refreshed_missing
    assert "songwriters" not in refreshed_missing
    assert refreshed["tracks"][1]["release_readiness"] == INCOMPLETE
    stored = json.loads(default_manifest_path(album["release_id"], artifact_root).read_text(encoding="utf-8"))
    assert stored["tracks"][1]["ingest_job_id"] == incomplete.job_id
    assert "USRC17607839" not in json.dumps(stored["tracks"])


def test_invalid_release_type_is_refused(tmp_path: Path, monkeypatch) -> None:
    _ingest_song(tmp_path, monkeypatch, name="demo.wav", frames=4410)
    with pytest.raises(ReleaseError) as exc:
        create_album_manifest(release_type="lp", artifact_root=tmp_path / "artifacts")
    assert exc.value.code == "INVALID_RELEASE_TYPE"
