"""ACI-A2L-REL-004 release package export. Do not invent missing release data."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from a2l.album_manifest import create_album_manifest, save_album_manifest
from a2l.approve import default_approved_txt_path
from a2l.export import INTERNAL_ARTIFACT_NAMES
from a2l.ingest import SOURCE_FILENAME
from a2l.release_package import export_release_package, package_download_name
from a2l.release_record import INCOMPLETE, READY
from tests.test_album_manifest import _ingest_song
from tests.test_album_readiness import _complete_song


def _zip_json(archive: ZipFile, name: str) -> dict:
    return json.loads(archive.read(name).decode("utf-8"))


def _open_package(result: dict) -> ZipFile:
    return ZipFile(result["zip_path"])


def test_ready_album_exports_zip_with_governed_contents(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="ready.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    _complete_song(song, tmp_path)
    source_wav = song.artifact_dir / "authoritative_source" / SOURCE_FILENAME
    source_bytes = source_wav.read_bytes()
    approved = default_approved_txt_path(song.job_id).read_text(encoding="utf-8")
    album = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=artifact_root,
        release_id="readyalbum004aaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    result = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:00:00+00:00")
    assert result["overall_state"] == READY
    assert result["download_name"] == "Jay_Garrett_Demo_Album_A2L_Release_Package.zip"
    assert result["zip_path"].is_file()
    assert result["authority"] == "DERIVED_RELEASE_PACKAGE_EXPORT"
    assert result["master_audio_included"] is False
    assert result["distributor_package"] is False
    assert result["relative_export_path"].startswith("releases/readyalbum004aaa/exports/")
    with _open_package(result) as archive:
        names = set(archive.namelist())
        assert "package_manifest.json" in names
        assert "release_summary.txt" in names
        assert "album/album_release_manifest.json" in names
        assert "album/album_release_readiness.json" in names
        assert "provenance/source_references.json" in names
        assert any(name.endswith("song_release_record.json") for name in names)
        for lyric_name in INTERNAL_ARTIFACT_NAMES.values():
            assert any(name.endswith(f"lyrics/{lyric_name}") for name in names)
        assert not any(name.lower().endswith(".wav") for name in names)
        manifest = _zip_json(archive, "package_manifest.json")
        assert manifest["package_type"] == "A2L_RELEASE_PREPARATION_PACKAGE"
        assert manifest["package_version"] == "1.0.0"
        assert manifest["release_id"] == album["release_id"]
        assert manifest["album_title"] == "Demo Album"
        assert manifest["primary_artist"] == "Jay Garrett"
        assert manifest["overall_state"] == READY
        assert manifest["generated_at"] == "2026-09-14T18:00:00+00:00"
        assert sorted(manifest["included_files"]) == sorted(archive.namelist())
        assert manifest["master_audio_included"] is False
        assert manifest["distributor_package"] is False
        assert "spotify" not in json.dumps(manifest).lower()
        summary = archive.read("release_summary.txt").decode("utf-8")
        assert "A2L INTERNAL RELEASE READINESS:\nREADY" in summary
        assert "Demo Album" in summary
        assert "Jay Garrett" in summary
        assert "01  Stomp To  READY" in summary
        assert "not proof of distributor acceptance" in summary
        album_stored = _zip_json(archive, "album/album_release_manifest.json")
        assert album_stored["authority"] == "ALBUM_RELEASE_MANIFEST"
        readiness = _zip_json(archive, "album/album_release_readiness.json")
        assert readiness["overall_state"] == READY
        track_record = _zip_json(archive, "tracks/01_Stomp_To/song_release_record.json")
        isrc = next(item for item in track_record["fields"] if item["id"] == "isrc")
        assert isrc["value"] is None
        assert "upc" not in json.dumps(track_record).lower()
        lyric_sheet = archive.read("tracks/01_Stomp_To/lyrics/lyric-sheet.txt").decode("utf-8")
        assert "Hook us with that old school funk" in lyric_sheet
        provenance = _zip_json(archive, "provenance/source_references.json")
        assert provenance["release_id"] == album["release_id"]
        assert provenance["album_manifest_ref"].endswith("album_release_manifest.json")
        assert provenance["album_readiness_ref"].endswith("album_release_readiness.json")
        audio = provenance["tracks"][0]["source_audio"]
        assert audio["included"] is False
        assert audio["source_sha256"] == song.job_id
        assert provenance["tracks"][0]["song_release_record_ref"]
        assert provenance["tracks"][0]["approved_lyrics_ref"]
    assert source_wav.read_bytes() == source_bytes
    assert default_approved_txt_path(song.job_id).read_text(encoding="utf-8") == approved
    sidecar = result["zip_path"].with_name("package_manifest.json")
    assert sidecar.is_file()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["authority"] == "DERIVED_RELEASE_PACKAGE_EXPORT"


def test_incomplete_album_can_export_and_preserves_gaps(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="gap.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    album = create_album_manifest(
        album_title="Demo Album",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=artifact_root,
        release_id="incomplete004aaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    result = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:10:00+00:00")
    assert result["overall_state"] == INCOMPLETE
    with _open_package(result) as archive:
        summary = archive.read("release_summary.txt").decode("utf-8")
        assert "A2L INTERNAL RELEASE READINESS:\nINCOMPLETE" in summary
        assert "MISSING — BLOCKING" in summary
        assert "Approved lyrics" in summary
        manifest = _zip_json(archive, "package_manifest.json")
        assert manifest["overall_state"] == INCOMPLETE
        assert manifest["completeness"]["missing_approved_lyrics"]
        names = archive.namelist()
        assert not any("/lyrics/" in name for name in names)
        record = _zip_json(archive, "tracks/01_Stomp_To/song_release_record.json")
        lyrics = next(item for item in record["fields"] if item["id"] == "approved_lyrics")
        assert lyrics["status"] == "MISSING"
        assert lyrics["value"] is None
        isrc = next(item for item in record["fields"] if item["id"] == "isrc")
        assert isrc["value"] is None


def test_missing_identity_uses_release_id_filename_and_does_not_invent(tmp_path: Path, monkeypatch) -> None:
    _ingest_song(tmp_path, monkeypatch, name="anon.wav", frames=4410)
    album = create_album_manifest(artifact_root=tmp_path / "artifacts", release_id="noidalbum004aaa")
    result = export_release_package(album["release_id"], artifact_root=tmp_path / "artifacts", now="2026-09-14T18:20:00+00:00")
    assert result["download_name"] == "noidalbum004aaa_A2L_Release_Package.zip"
    assert result["album_title"] is None
    assert result["primary_artist"] is None
    with _open_package(result) as archive:
        summary = archive.read("release_summary.txt").decode("utf-8")
        assert "Album Title: MISSING" in summary
        assert "Primary Artist: MISSING" in summary
        assert "Untitled" not in summary
        manifest = _zip_json(archive, "package_manifest.json")
        assert manifest["album_title"] is None
        assert manifest["primary_artist"] is None


def test_unsafe_filename_characters_are_sanitized(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="safe.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    _complete_song(song, tmp_path)
    album = create_album_manifest(
        album_title="A/B: Hits?*",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=artifact_root,
        release_id="unsafealbum004aa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    result = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T18:30:00+00:00")
    assert "/" not in result["download_name"]
    assert ":" not in result["download_name"]
    assert "*" not in result["download_name"]
    assert "?" not in result["download_name"]
    assert result["download_name"].endswith("_A2L_Release_Package.zip")
    assert result["download_name"].startswith("Jay_Garrett_")
    assert package_download_name("A/B: Hits?*", "Jay Garrett", album["release_id"]) == result["download_name"]


def test_track_order_matches_manifest_and_reexport_uses_current_truth(tmp_path: Path, monkeypatch) -> None:
    first, artifact_root = _ingest_song(tmp_path, monkeypatch, name="one.wav", frames=4410, title="Song A", artist="Jay Garrett")
    second, _ = _ingest_song(tmp_path, monkeypatch, name="two.wav", frames=8820, title="Song B", artist="Jay Garrett")
    _complete_song(first, tmp_path)
    album = create_album_manifest(
        album_title="Ordered",
        primary_artist="Jay Garrett",
        release_type="album",
        artifact_root=artifact_root,
        release_id="orderalbum004aaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [second.job_id, first.job_id]}, artifact_root=artifact_root)
    first_export = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T19:00:00+00:00")
    assert first_export["overall_state"] == INCOMPLETE
    with _open_package(first_export) as archive:
        names = archive.namelist()
        assert "tracks/01_Song_B/song_release_record.json" in names
        assert "tracks/02_Song_A/song_release_record.json" in names
        summary = archive.read("release_summary.txt").decode("utf-8")
        assert "01  Song B  INCOMPLETE" in summary
        assert "02  Song A  READY" in summary
        first_record = _zip_json(archive, "tracks/01_Song_B/song_release_record.json")
        writers = next(item for item in first_record["fields"] if item["id"] == "songwriters")
        assert writers["status"] == "MISSING"
        assert not writers["value"]
    _complete_song(second, tmp_path, extra={"copyright_year": "2025"})
    second_export = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T19:05:00+00:00")
    assert second_export["overall_state"] == READY
    assert first_export["zip_path"].is_file()
    assert second_export["zip_path"] != first_export["zip_path"]
    with _open_package(first_export) as archive:
        assert _zip_json(archive, "package_manifest.json")["overall_state"] == INCOMPLETE
        first_record = _zip_json(archive, "tracks/01_Song_B/song_release_record.json")
        writers = next(item for item in first_record["fields"] if item["id"] == "songwriters")
        assert writers["status"] == "MISSING"
        assert not writers["value"]
    with _open_package(second_export) as archive:
        assert _zip_json(archive, "package_manifest.json")["overall_state"] == READY
        updated = _zip_json(archive, "tracks/01_Song_B/song_release_record.json")
        writers = next(item for item in updated["fields"] if item["id"] == "songwriters")
        year = next(item for item in updated["fields"] if item["id"] == "copyright_year")
        assert writers["value"] == ["Jay Garrett"]
        assert year["value"] == "2025"
        summary = archive.read("release_summary.txt").decode("utf-8")
        assert "A2L INTERNAL RELEASE READINESS:\nREADY" in summary
        assert "tracks/01_Song_B/lyrics/lyric-sheet.txt" in archive.namelist()


def test_existing_album_and_song_artifacts_remain_source_authority(tmp_path: Path, monkeypatch) -> None:
    song, artifact_root = _ingest_song(tmp_path, monkeypatch, name="keep.wav", frames=4410, title="Stomp To", artist="Jay Garrett")
    _complete_song(song, tmp_path, extra={"isrc": "USRC17607839"})
    album = create_album_manifest(
        album_title="Keep",
        primary_artist="Jay Garrett",
        release_type="ep",
        artifact_root=artifact_root,
        release_id="keepalbum004aaaa",
    )
    save_album_manifest(album["release_id"], {"track_ids": [song.job_id]}, artifact_root=artifact_root)
    manifest_path = artifact_root / "releases" / album["release_id"] / "album_release_manifest.json"
    before_manifest = manifest_path.read_text(encoding="utf-8")
    before_record = (song.artifact_dir / "song_release_record.json").read_text(encoding="utf-8")
    result = export_release_package(album["release_id"], artifact_root=artifact_root, now="2026-09-14T19:10:00+00:00")
    assert result["overall_state"] == READY
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert stored["authority"] == "ALBUM_RELEASE_MANIFEST"
    assert stored["album_ready_determination"] is False
    assert json.loads(before_manifest)["tracks"] == stored["tracks"]
    after_record = json.loads((song.artifact_dir / "song_release_record.json").read_text(encoding="utf-8"))
    assert json.loads(before_record)["operator"] == after_record["operator"]
    with _open_package(result) as archive:
        packaged = _zip_json(archive, "tracks/01_Stomp_To/song_release_record.json")
        isrc = next(item for item in packaged["fields"] if item["id"] == "isrc")
        assert isrc["value"] == "USRC17607839"
        assert archive.read("album/album_release_manifest.json").decode("utf-8") == manifest_path.read_text(encoding="utf-8")
