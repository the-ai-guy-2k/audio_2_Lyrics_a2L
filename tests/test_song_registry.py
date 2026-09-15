"""ACI-A2L-DM-002 Song Registry tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.errors import SongRegistryError
from a2l.ingest import ingest_wav
from a2l.pipeline import LOCKED_SHA256, ROOT
from a2l.song_registry import (
    RECORD_TYPE_REGISTRY,
    RECORD_TYPE_SONG,
    associate_master,
    default_registry_path,
    find_song_id_for_ingest,
    get_song,
    list_songs,
    load_registry,
    register_song,
)
from tests.wav_fixtures import write_pcm_wav

def _seed_ingest(tmp_path: Path, name: str = "song.wav") -> str:
    source = write_pcm_wav(tmp_path / name)
    result = ingest_wav(source, tmp_path / "artifacts")
    return result.job_id


def test_register_list_get_and_persist(tmp_path: Path) -> None:
    job = _seed_ingest(tmp_path)
    first = register_song(job, artifact_root=tmp_path / "artifacts")
    assert first["record_type"] == RECORD_TYPE_SONG
    assert first["song_id"]
    assert first["song_id"] != job
    assert len(first["song_id"]) == 32
    assert first["identity"]["title"]["status"] == "MISSING"
    assert first["identity"]["artist"]["status"] == "MISSING"
    assert first["source"]["current_master_revision"] == 1
    assert first["source"]["masters"][0]["source_sha256"] == job
    assert first["source"]["masters"][0]["ingest_job_id"] == job

    path = default_registry_path(tmp_path / "artifacts")
    assert path.is_file()
    store = json.loads(path.read_text(encoding="utf-8"))
    assert store["record_type"] == RECORD_TYPE_REGISTRY
    assert store["schema_version"] == "1.0.0"
    assert store["by_ingest_job_id"][job] == first["song_id"]

    reloaded = load_registry(tmp_path / "artifacts")
    assert reloaded["songs"][first["song_id"]]["song_id"] == first["song_id"]
    listed = list_songs(tmp_path / "artifacts")
    assert len(listed) == 1
    assert listed[0]["song_id"] == first["song_id"]
    assert listed[0]["title"]["status"] == "MISSING"
    assert listed[0]["current_ingest_job_id"] == job
    fetched = get_song(first["song_id"], artifact_root=tmp_path / "artifacts")
    assert fetched["song_id"] == first["song_id"]


def test_register_is_idempotent_for_same_ingest(tmp_path: Path) -> None:
    job = _seed_ingest(tmp_path)
    first = register_song(job, artifact_root=tmp_path / "artifacts")
    second = register_song(job, artifact_root=tmp_path / "artifacts")
    assert first["song_id"] == second["song_id"]
    assert len(list_songs(tmp_path / "artifacts")) == 1
    assert find_song_id_for_ingest(job, artifact_root=tmp_path / "artifacts") == first["song_id"]


def test_song_id_must_not_equal_ingest_sha(tmp_path: Path) -> None:
    job = _seed_ingest(tmp_path)
    with pytest.raises(SongRegistryError) as failed:
        register_song(job, artifact_root=tmp_path / "artifacts", song_id=job)
    assert failed.value.code == "INVALID_SONG_ID"


def test_associate_master_allows_multi_master_same_song(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    job_a = _seed_ingest(tmp_path, "a.wav")
    # second wav with different content/hash
    source_b = write_pcm_wav(tmp_path / "b.wav", frame_count=22050)
    job_b = ingest_wav(source_b, artifacts).job_id
    assert job_a != job_b

    song = register_song(job_a, artifact_root=artifacts)
    updated = associate_master(song["song_id"], job_b, artifact_root=artifacts, make_current=True)
    masters = updated["source"]["masters"]
    assert len(masters) == 2
    assert updated["song_id"] == song["song_id"]
    assert updated["source"]["current_master_revision"] == 2
    roles = {item["ingest_job_id"]: item["role"] for item in masters}
    assert roles[job_a] == "SUPERSEDED"
    assert roles[job_b] == "CURRENT"
    assert find_song_id_for_ingest(job_a, artifact_root=artifacts) == song["song_id"]
    assert find_song_id_for_ingest(job_b, artifact_root=artifacts) == song["song_id"]


def test_filename_not_used_as_title(tmp_path: Path) -> None:
    job = _seed_ingest(tmp_path, "Totally Not A Title.wav")
    song = register_song(job, artifact_root=tmp_path / "artifacts")
    assert song["identity"]["title"]["status"] == "MISSING"
    assert song["identity"]["title"]["value"] is None


def test_jay_song_registers_and_resolves_governed_refs() -> None:
    jay = ROOT / "artifacts" / "ingest" / LOCKED_SHA256
    if not (jay / "ingest_manifest.json").is_file():
        pytest.skip("Locked Jay ingest artifacts not present on this workstation")

    first = register_song(LOCKED_SHA256, artifact_root=ROOT / "artifacts")
    second = register_song(LOCKED_SHA256, artifact_root=ROOT / "artifacts")
    assert first["song_id"] == second["song_id"]
    assert first["song_id"] != LOCKED_SHA256
    assert first["source"]["masters"][0]["source_sha256"] == LOCKED_SHA256
    assert first["source"]["masters"][0]["source_ref"].endswith("authoritative_source/source.wav")
    assert first["identity"]["title"]["status"] in {"AVAILABLE", "MISSING"}
    assert first["identity"]["title"].get("value") != "01Stomp to MIX MSTR 24bit_48hz.wav"
    if (jay / "a2l_pipeline" / "approved_lyrics" / "approved_lyrics.json").is_file():
        assert first["lyrics"]["approval_status"] == "APPROVED"
        assert first["lyrics"]["approved_lyrics_ref"]
    if (jay / "song_intelligence_record.json").is_file():
        assert first["intelligence"]["sir_ref"]
        assert first["intelligence"]["sir_status"] == "AVAILABLE"
        assert "rhythm_structure" in first["intelligence"]
        assert "key_mode" in first["intelligence"]
        assert "audio_intelligence" in first["intelligence"]
        assert "lyric_intelligence" in first["intelligence"]
    if (jay / "song_release_record.json").is_file():
        assert first["release"]["song_release_record_ref"]
    source = jay / "authoritative_source" / "source.wav"
    before = source.read_bytes()
    get_song(first["song_id"], artifact_root=ROOT / "artifacts")
    assert source.read_bytes() == before
