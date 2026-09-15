"""ACI-A2L-SI-011 Song Intelligence product UI. Do not use the locked Jay song."""

from __future__ import annotations

import json
import threading
import time
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from a2l.app_server import AppHandler, AppState
from a2l.approve import approve_reviewed_lyrics
from a2l.engines import EngineResult, EngineSegment, ScriptedEngine
from a2l.ingest import ingest_wav
from a2l.metadata import apply_song_metadata, write_song_metadata
from a2l.pipeline import LOCKED_SHA256
from a2l.review import apply_corrections, review_from_structured, save_review
from a2l.song_intelligence import (
    AGGREGATION_KIND,
    DEFAULT_CAPABILITY,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_UNAVAILABLE,
    catalog_payload,
    resolve_engines,
    run_analysis,
)
from a2l.song_intelligence_record import RECORD_TYPE, RUN_NOT_RUN
from tests.test_review import _structured
from tests.wav_fixtures import write_pcm_wav


def _engine() -> ScriptedEngine:
    return ScriptedEngine(
        EngineResult(
            technology="faster-whisper",
            model="large-v3",
            text="Play something we can stomp to",
            language="en",
            segments=(EngineSegment(0.0, 2.0, "Play something we can stomp to", -0.2, 0.1, 1.1),),
            configuration={"mode": "test"},
        )
    )


def _fake_runners(failing: str | None = None) -> dict:
    def lyrics(song):
        approved = song.get("approved_lyrics")
        if not approved:
            return {
                "status": STATUS_UNAVAILABLE,
                "message": "Unavailable — Approved Lyrics Required",
                "fields": [
                    {
                        "id": "approved_lyric_status",
                        "group": "lyrics",
                        "label": "Approved lyric status",
                        "value": "Unavailable — Approved Lyrics Required",
                        "engine_id": "lyrics_workflow",
                        "engine_label": "Approved Lyrics",
                        "engine_technical": "Existing A2L lyric transcription and approval workflow",
                        "authority": "AUTHORITATIVE INPUT",
                        "status": STATUS_UNAVAILABLE,
                        "validation_state": "",
                        "evidence": [],
                        "note": "",
                    }
                ],
            }
        return {
            "status": STATUS_COMPLETE,
            "message": "",
            "fields": [
                {
                    "id": "approved_lyrics",
                    "group": "lyrics",
                    "label": "Approved lyrics",
                    "value": approved["text"],
                    "engine_id": "lyrics_workflow",
                    "engine_label": "Approved Lyrics",
                    "engine_technical": "Existing A2L lyric transcription and approval workflow",
                    "authority": "AUTHORITATIVE",
                    "status": STATUS_COMPLETE,
                    "validation_state": "",
                    "evidence": [],
                    "note": "",
                }
            ],
        }

    def complete(engine_id, group, label, value, status=STATUS_COMPLETE, authority="MACHINE-DERIVED"):
        def runner(_song):
            if failing == engine_id:
                raise RuntimeError("forced failure")
            return {
                "status": status,
                "message": "",
                "fields": [
                    {
                        "id": engine_id,
                        "group": group,
                        "label": label,
                        "value": value,
                        "engine_id": engine_id,
                        "engine_label": label,
                        "engine_technical": engine_id,
                        "authority": authority,
                        "status": status,
                        "validation_state": "PENDING HUMAN VALIDATION",
                        "evidence": [{"label": "score", "value": 0.17}],
                        "note": "Partial" if status == STATUS_PARTIAL else "",
                    }
                ],
            }

        return runner

    def lyric_intelligence(song):
        if not song.get("approved_lyrics"):
            return {
                "status": STATUS_UNAVAILABLE,
                "message": "Unavailable — Approved Lyrics Required",
                "fields": [],
            }
        if failing == "lyric_intelligence":
            raise RuntimeError("forced failure")
        return {
            "status": STATUS_COMPLETE,
            "message": "",
            "fields": [
                {
                    "id": "lyric_intelligence",
                    "group": "meaning",
                    "label": "Themes",
                    "value": ["play something we can stomp to"],
                    "engine_id": "lyric_intelligence",
                    "engine_label": "Lyric Intelligence",
                    "engine_technical": "lyric_intelligence",
                    "authority": "MACHINE-DERIVED",
                    "status": STATUS_COMPLETE,
                    "validation_state": "PENDING HUMAN VALIDATION",
                    "evidence": [],
                    "note": "",
                }
            ],
        }

    return {
        "lyrics_workflow": lyrics,
        "rhythm_structure": complete("rhythm_structure", "music", "BPM", 98),
        "key_mode": complete("key_mode", "music", "Key", "A"),
        "clap_audio": complete("clap_audio", "sound", "Vocal Characteristics", "ensemble label", status=STATUS_PARTIAL),
        "ast_genre": complete("ast_genre", "sound", "Genre / Style", "Grunge"),
        "panns_instrumentation": complete(
            "panns_instrumentation", "sound", "Instrumentation", "Guitar", status=STATUS_PARTIAL
        ),
        "lyric_intelligence": lyric_intelligence,
    }


def _start(tmp_path: Path, monkeypatch, runners=None):
    artifact_root = tmp_path / "artifacts"

    def job_dir(sha=LOCKED_SHA256, artifact_root=artifact_root):
        return artifact_root / "ingest" / sha

    monkeypatch.setattr("a2l.review.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", job_dir)
    app = AppState(artifact_root=artifact_root, engine=_engine(), si_runners=runners or _fake_runners())
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(AppHandler, app=app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return app, server, server.server_address[1], artifact_root


def _request(port: int, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data, response


def _wait_si(port: int, timeout: float = 8.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        status, data, _ = _request(port, "GET", "/api/song-intelligence")
        last = json.loads(data.decode("utf-8"))
        if status == 200 and last.get("ok") and not last.get("busy"):
            return last
        time.sleep(0.05)
    return last


def _ingest(tmp_path: Path, monkeypatch, name: str = "demo.wav"):
    wav = write_pcm_wav(tmp_path / name)
    ingest = ingest_wav(wav, tmp_path / "artifacts")
    monkeypatch.setattr("a2l.review.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    write_song_metadata(ingest.job_id, "Stomp To", "Jay Garrett", job_dir=ingest.artifact_dir)
    return ingest


def _approve(ingest, tmp_path: Path):
    review = review_from_structured(_structured(tmp_path), tmp_path / "s.json", ingest.job_id)
    apply_corrections(review, {1: "Play something we can stomp to"})
    apply_song_metadata(review, "Stomp To", "Jay Garrett")
    save_review(review, sha=ingest.job_id)
    return approve_reviewed_lyrics(review, ingest.job_id, confirm=True, now="2026-09-15T00:00:00+00:00")


def test_page_exposes_song_intelligence(tmp_path: Path, monkeypatch) -> None:
    _app, server, port, _root = _start(tmp_path, monkeypatch)
    try:
        status, data, _ = _request(port, "GET", "/")
        html = data.decode("utf-8")
        assert status == 200
        assert "Song Intelligence" in html
        assert "Analyze song" in html
        assert "Full Song Intelligence" in html
        assert "Advanced engine selection" in html
        assert "Extract lyrics" in html
        assert "SHA" not in html
        assert LOCKED_SHA256 not in html
        catalog = json.loads(_request(port, "GET", "/api/song-intelligence-catalog")[1].decode("utf-8"))
        assert catalog["default_capability"] == DEFAULT_CAPABILITY
        engine_ids = [item["id"] for item in catalog["engines"]]
        assert engine_ids == [
            "lyrics_workflow",
            "rhythm_structure",
            "key_mode",
            "clap_audio",
            "ast_genre",
            "panns_instrumentation",
            "lyric_intelligence",
        ]
    finally:
        server.shutdown()


def test_full_and_selective_analysis_and_provenance(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _approve(ingest, tmp_path)
    source_before = (ingest.artifact_dir / "authoritative_source" / "source.wav").read_bytes()
    _app, server, port, _root = _start(tmp_path, monkeypatch)
    try:
        status, data, _ = _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps({"ingest_job_id": ingest.job_id, "capability": "full_song_intelligence"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        result = _wait_si(port)
        assert result["song_intelligence_record"] is True
        assert result["kind"] == RECORD_TYPE
        assert result["usable_as_song_facts"] is False
        fields = {item["id"]: item for item in result["fields"]}
        assert fields["approved_lyrics"]["authority"] == "AUTHORITATIVE"
        assert fields["key_mode"]["authority"] == "MACHINE-DERIVED"
        assert fields["clap_audio"]["status"] == STATUS_PARTIAL
        assert fields["panns_instrumentation"]["status"] == STATUS_PARTIAL
        assert fields["panns_instrumentation"]["note"] == "Partial"
        assert fields["ast_genre"]["engine_id"] == "ast_genre"
        assert "PENDING HUMAN VALIDATION" in fields["key_mode"]["validation_state"]
        assert result["master_hash_unchanged"] is True
        assert result["revision"] == 1
        assert (ingest.artifact_dir / "song_intelligence_record.json").is_file()
        assert (ingest.artifact_dir / "authoritative_source" / "source.wav").read_bytes() == source_before

        status, data, _ = _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps({"ingest_job_id": ingest.job_id, "capability": "key_mode"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        selected = _wait_si(port)
        assert selected["capability"] == "key_mode"
        assert selected["engines_requested"] == ["key_mode"]
        assert selected["revision"] == 2
        module_ids = [item["id"] for item in selected["modules"]]
        assert "key_mode" in module_ids
        assert selected["kind"] == RECORD_TYPE
    finally:
        server.shutdown()


def test_advanced_engine_selection_and_lyrics_dependency(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _app, server, port, _root = _start(tmp_path, monkeypatch)
    try:
        status, data, _ = _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps(
                {
                    "ingest_job_id": ingest.job_id,
                    "capability": "audio_intelligence",
                    "engines": ["ast_genre"],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        result = _wait_si(port)
        assert result["engines_requested"] == ["ast_genre"]
        values = {item["id"]: item["value"] for item in result["fields"]}
        assert values["ast_genre"] == "Grunge"

        status, data, _ = _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps({"ingest_job_id": ingest.job_id, "capability": "lyric_intelligence"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        missing = _wait_si(port)
        by_id = {item["id"]: item for item in missing["modules"]}
        assert by_id["lyric_intelligence"]["status"] == STATUS_UNAVAILABLE
        assert "Approved Lyrics Required" in by_id["lyric_intelligence"]["message"]
    finally:
        server.shutdown()


def test_failure_isolation_keeps_successful_modules(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _approve(ingest, tmp_path)
    _app, server, port, _root = _start(tmp_path, monkeypatch, runners=_fake_runners(failing="panns_instrumentation"))
    try:
        _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps({"ingest_job_id": ingest.job_id, "capability": "audio_intelligence"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        result = _wait_si(port)
        by_id = {item["id"]: item for item in result["modules"]}
        assert by_id["clap_audio:vocal_characteristics"]["status"] == STATUS_PARTIAL
        assert by_id["ast_genre"]["status"] == STATUS_COMPLETE
        assert by_id["panns_instrumentation"]["status"] == STATUS_FAILED
        values = {item["id"]: item["value"] for item in result["fields"]}
        assert values["ast_genre"] == "Grunge"
    finally:
        server.shutdown()


def test_advanced_cannot_expand_beyond_capability() -> None:
    with pytest.raises(Exception):
        resolve_engines("key_mode", ["ast_genre"])
    assert resolve_engines("full_song_intelligence", ["key_mode", "ast_genre"]) == ["key_mode", "ast_genre"]
    assert resolve_engines("audio_intelligence", None) == ["clap_audio", "ast_genre", "panns_instrumentation"]


def test_aggregation_is_not_a_record(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    display = run_analysis(
        ingest.job_id,
        "rhythm_structure",
        None,
        tmp_path / "artifacts",
        runners=_fake_runners(),
    )
    assert display["kind"] == RECORD_TYPE
    assert display["song_intelligence_record"] is True
    assert display["usable_as_song_facts"] is False
    stored = json.loads((ingest.artifact_dir / "song_intelligence_ui" / "ui_aggregation.json").read_text(encoding="utf-8"))
    assert stored["kind"] == AGGREGATION_KIND
    assert stored["song_intelligence_record"] is False
    assert stored["outranks_sir"] is False
    sir = json.loads((ingest.artifact_dir / "song_intelligence_record.json").read_text(encoding="utf-8"))
    assert sir["record_type"] == RECORD_TYPE
    assert sir["rhythm_structure"]["run_state"] != RUN_NOT_RUN
    assert sir["key_mode"]["run_state"] == RUN_NOT_RUN
    catalog = catalog_payload(tmp_path / "artifacts")
    assert catalog["songs"][0]["song_title"] == "Stomp To"
