"""ACI-A2L-010 operator application tests. Do not use the locked Jay song."""

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
from a2l.engines import EngineResult, EngineSegment, ScriptedEngine
from a2l.pipeline import LOCKED_SHA256
from tests.wav_fixtures import pcm_wav_bytes, truncated_wav_bytes, write_pcm_wav


def _engine(delay: float = 0.0) -> ScriptedEngine:
    result = EngineResult(
        technology="faster-whisper",
        model="large-v3",
        text="Play something we can stomp to Thanks for watching!",
        language="en",
        segments=(
            EngineSegment(0.0, 2.0, "Play something we can stomp to", -0.2, 0.1, 1.1),
            EngineSegment(2.0, 4.0, "Thanks for watching!", -1.3, 0.7, 1.2),
        ),
        configuration={"mode": "test"},
    )
    if delay <= 0:
        return ScriptedEngine(result)

    class SlowEngine(ScriptedEngine):
        def transcribe(self, wav_path: Path) -> EngineResult:
            time.sleep(delay)
            return super().transcribe(wav_path)

    return SlowEngine(result)


def _multipart(
    filename: str,
    data: bytes,
    engine: str | None = None,
    song_title: str | None = None,
    artist: str | None = None,
) -> tuple[str, bytes]:
    boundary = "----A2LTestBoundary"
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="wav"; filename="{filename}"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8")
        + data
    ]
    if engine is not None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="engine"\r\n\r\n'
                f"{engine}"
            ).encode("utf-8")
        )
    if song_title is not None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="song_title"\r\n\r\n'
                f"{song_title}"
            ).encode("utf-8")
        )
    if artist is not None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="artist"\r\n\r\n'
                f"{artist}"
            ).encode("utf-8")
        )
    return boundary, b"\r\n".join(parts) + f"\r\n--{boundary}--\r\n".encode("utf-8")


def _start(tmp_path: Path, monkeypatch, engine=None):
    artifact_root = tmp_path / "artifacts"

    def job_dir(sha=LOCKED_SHA256, artifact_root=artifact_root):
        return artifact_root / "ingest" / sha

    monkeypatch.setattr("a2l.review.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", job_dir)
    app = AppState(artifact_root=artifact_root, engine=engine or _engine())
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(AppHandler, app=app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return app, server, server.server_address[1]


def _request(port: int, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data, response


def _wait_ready(port: int, timeout: float = 8.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        status, data, _ = _request(port, "GET", "/api/session")
        last = json.loads(data.decode("utf-8"))
        if status == 200 and last.get("ok") and not last.get("busy"):
            return last
        time.sleep(0.05)
    return last


def test_app_page_loads(tmp_path: Path, monkeypatch) -> None:
    app, server, port = _start(tmp_path, monkeypatch)
    try:
        status, data, _ = _request(port, "GET", "/")
        html = data.decode("utf-8")
        assert status == 200
        assert "Extract lyrics" in html
        assert "Mark lyrics APPROVED" in html
        assert "Download" in html
        assert "SHA" not in html
        assert LOCKED_SHA256 not in html
        session = json.loads(_request(port, "GET", "/api/session")[1].decode("utf-8"))
        assert session["has_job"] is False
        assert session["can_album"] is True
        assert app.job_id == ""
    finally:
        server.shutdown()


def test_rejects_invalid_upload(tmp_path: Path, monkeypatch) -> None:
    _, server, port = _start(tmp_path, monkeypatch)
    try:
        boundary, body = _multipart("song.txt", b"not audio")
        status, data, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        payload = json.loads(data.decode("utf-8"))
        assert status == 400
        assert payload["ok"] is False
        assert payload["error"] == "Please choose a WAV file."
        boundary, body = _multipart("song.wav", truncated_wav_bytes())
        _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        session = _wait_ready(port)
        assert session["can_review"] is False
        assert session["error"]
        assert "python" not in session["error"].lower()
        assert "ACI-" not in session["error"]
        assert "artifact" not in session["error"].lower()
    finally:
        server.shutdown()


def test_session_poll_during_extract_does_not_break_pipeline(tmp_path: Path, monkeypatch) -> None:
    _, server, port = _start(tmp_path, monkeypatch, engine=_engine(delay=0.35))
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes())
        status, _, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert status == 200
        seen_processing = False
        deadline = time.time() + 8
        while time.time() < deadline:
            session = json.loads(_request(port, "GET", "/api/session")[1].decode("utf-8"))
            if session.get("busy"):
                seen_processing = True
                assert session["error"] == ""
                assert session["screen"] == "processing"
            elif seen_processing:
                assert session["error"] == ""
                assert session["can_review"] is True
                return
            time.sleep(0.05)
        pytest.fail("extract did not finish")
    finally:
        server.shutdown()


def test_extract_review_save_approve_export(tmp_path: Path, monkeypatch) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    before = source.read_bytes()
    app, server, port = _start(tmp_path, monkeypatch)
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes())
        status, data, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert status == 200
        session = _wait_ready(port)
        assert session["error"] == ""
        assert session["can_review"] is True
        assert session["lyric_state"] in {"DRAFT", "REVIEWED"}
        assert session["filename"] == "demo.wav"
        assert session["song_title"] is None
        assert session["artist"] is None
        assert app.job_id
        assert app.job_id != LOCKED_SHA256
        assert source.read_bytes() == before

        status, data, _ = _request(port, "GET", "/api/state")
        state = json.loads(data.decode("utf-8"))
        assert status == 200
        assert "artifacts/ingest" not in json.dumps(state)
        lines = state["review"]["lines"]
        machine_line = next(item for item in lines if item.get("kind") != "time_gap")
        assert "Play something we can stomp to" in (machine_line.get("human_text") or "")
        assert "Thanks for watching!" in json.dumps(lines)

        save_body = json.dumps({
            "lines": [{"index": machine_line["index"], "human_text": "Play something we can groove to"}],
        }).encode("utf-8")
        status, data, _ = _request(
            port,
            "POST",
            "/api/save",
            body=save_body,
            headers={"Content-Type": "application/json"},
        )
        saved = json.loads(data.decode("utf-8"))
        assert status == 200
        assert saved["lyric_state"] != "APPROVED"
        export_status, export_body, _ = _request(port, "GET", "/api/export")
        assert export_status == 400
        export_payload = json.loads(export_body.decode("utf-8"))
        assert export_payload["error_code"] == "NOT_APPROVED"
        canonical_status, _, _ = _request(port, "GET", "/export/approved_lyrics.txt")
        assert canonical_status == 400

        status, data, _ = _request(
            port,
            "POST",
            "/api/approve",
            body=b'{"confirm": false}',
            headers={"Content-Type": "application/json"},
        )
        refused = json.loads(data.decode("utf-8"))
        assert status == 400
        assert refused["error_code"] == "APPROVAL_NOT_EXPLICIT"

        status, data, _ = _request(
            port,
            "POST",
            "/api/approve",
            body=b'{"confirm": true}',
            headers={"Content-Type": "application/json"},
        )
        approved = json.loads(data.decode("utf-8"))
        assert status == 200
        assert approved["lyric_state"] == "APPROVED"
        assert approved["review"]["authority"] == "HUMAN_REVIEW_PROVENANCE"
        assert approved["review"]["active_lyric_authority"] == "AUTHORITATIVE_APPROVED_LYRICS"

        status, data, headers = _request(port, "GET", "/export/approved_lyrics.txt")
        canonical = data.decode("utf-8")
        assert status == 200
        assert "Play something we can groove to" in canonical
        assert "00:" not in canonical
        assert "UNCERTAIN" not in canonical
        assert "approved_lyrics.txt" in (headers.getheader("Content-Disposition") or "")
        canonical_bytes = data

        status, data, _ = _request(port, "GET", "/api/export")
        sheet = json.loads(data.decode("utf-8"))
        assert status == 200
        assert sheet["format"] == "standard-lyric-sheet"
        assert sheet["format_label"] == "STANDARD LYRIC SHEET"
        assert sheet["usable_as_approved_lyrics"] is False
        assert sheet["text"] == canonical
        assert "Play something we can groove to" in sheet["text"]

        status, data, _ = _request(port, "GET", "/api/export?format=plain-text")
        plain = json.loads(data.decode("utf-8"))
        assert status == 200
        assert plain["format"] == "plain-text"
        assert plain["text"] == canonical

        status, data, headers = _request(port, "GET", "/export/output.txt?format=standard-lyric-sheet")
        assert status == 200
        assert data.decode("utf-8") == sheet["text"]
        disposition = headers.getheader("Content-Disposition") or ""
        assert "lyrics.txt" in disposition
        assert sheet["download_name"] == "lyrics.txt"
        assert _request(port, "GET", "/export/approved_lyrics.txt")[1] == canonical_bytes

        status, data, _ = _request(port, "GET", "/export/approved_lyrics.json")
        record = json.loads(data.decode("utf-8"))
        assert status == 200
        assert record["approval_event"]["automatic"] is False
        assert record["transcription_engine"] == "faster-whisper"
        assert record.get("song_title") is None
        assert record.get("artist") is None
        assert not sheet["text"].startswith("demo")
        assert "demo.wav" not in sheet["text"]

        status, data, _ = _request(
            port,
            "POST",
            "/api/reopen",
            body=b'{"confirm": true}',
            headers={"Content-Type": "application/json"},
        )
        reopened = json.loads(data.decode("utf-8"))
        assert status == 200
        assert reopened["lyric_state"] == "REQUIRES_REAPPROVAL"
        session = json.loads(_request(port, "GET", "/api/session")[1].decode("utf-8"))
        assert session["can_export"] is False
        assert source.read_bytes() == before
    finally:
        server.shutdown()


def test_extract_metadata_persists_and_appears_on_standard_sheet(tmp_path: Path, monkeypatch) -> None:
    app, server, port = _start(tmp_path, monkeypatch)
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes(), song_title="Stomp", artist="Jay")
        status, _, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert status == 200
        session = _wait_ready(port)
        assert session["error"] == ""
        assert session["song_title"] == "Stomp"
        assert session["artist"] == "Jay"
        assert session["filename"] == "demo.wav"

        status, data, _ = _request(port, "GET", "/api/state")
        state = json.loads(data.decode("utf-8"))
        assert status == 200
        assert state["review"]["song_title"] == "Stomp"
        assert state["review"]["artist"] == "Jay"
        machine_line = next(item for item in state["review"]["lines"] if item.get("kind") != "time_gap")

        save_body = json.dumps({
            "lines": [{"index": machine_line["index"], "human_text": machine_line["human_text"]}],
            "song_title": "Stomp Corrected",
            "artist": "Jay",
        }).encode("utf-8")
        status, data, _ = _request(
            port,
            "POST",
            "/api/save",
            body=save_body,
            headers={"Content-Type": "application/json"},
        )
        saved = json.loads(data.decode("utf-8"))
        assert status == 200
        assert saved["review"]["song_title"] == "Stomp Corrected"
        assert saved["lyric_state"] != "APPROVED"

        status, data, _ = _request(
            port,
            "POST",
            "/api/approve",
            body=b'{"confirm": true}',
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        canonical = _request(port, "GET", "/export/approved_lyrics.txt")[1].decode("utf-8")
        record = json.loads(_request(port, "GET", "/export/approved_lyrics.json")[1].decode("utf-8"))
        sheet = json.loads(_request(port, "GET", "/api/export")[1].decode("utf-8"))
        plain = json.loads(_request(port, "GET", "/api/export?format=plain-text")[1].decode("utf-8"))
        assert record["song_title"] == "Stomp Corrected"
        assert record["artist"] == "Jay"
        assert "Stomp Corrected" not in canonical
        assert sheet["text"].startswith("Stomp Corrected\nJay\n\n")
        assert sheet["text"].endswith(canonical)
        assert plain["text"] == canonical
        assert sheet["download_name"] == "Jay - Stomp Corrected.txt"
        assert plain["download_name"] == "Jay - Stomp Corrected - Plain Text.txt"
        status, data, headers = _request(port, "GET", "/export/output.txt?format=standard-lyric-sheet")
        assert status == 200
        assert 'filename="Jay - Stomp Corrected.txt"' in (headers.getheader("Content-Disposition") or "")
        assert data.decode("utf-8") == sheet["text"]
        status, data, headers = _request(port, "GET", "/export/output.txt?format=plain-text")
        assert status == 200
        assert "Jay - Stomp Corrected - Plain Text.txt" in (headers.getheader("Content-Disposition") or "")
        assert data.decode("utf-8") == canonical
        assert "demo.wav" not in sheet["text"]
        assert app.job_id
    finally:
        server.shutdown()


def test_release_record_round_trip_and_readiness(tmp_path: Path, monkeypatch) -> None:
    app, server, port = _start(tmp_path, monkeypatch)
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes(), song_title="Stomp To", artist="Jay Garrett")
        assert _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )[0] == 200
        session = _wait_ready(port)
        assert session["can_release"] is True
        status, data, _ = _request(port, "GET", "/api/release-record")
        record = json.loads(data.decode("utf-8"))
        assert status == 200
        fields = {item["id"]: item for item in record["fields"]}
        assert fields["song_title"]["status"] == "AVAILABLE"
        assert fields["song_title"]["value"] == "Stomp To"
        assert fields["primary_artist"]["value"] == "Jay Garrett"
        assert fields["track_duration"]["status"] == "AVAILABLE"
        assert fields["master_audio"]["status"] == "AVAILABLE"
        assert fields["approved_lyrics"]["status"] == "MISSING"
        assert fields["songwriters"]["status"] == "MISSING"
        assert fields["isrc"]["status"] == "MISSING"
        assert fields["isrc"]["value"] is None
        assert record["release_readiness"] == "INCOMPLETE"
        assert "demo.wav" not in json.dumps(fields["song_title"])

        save_body = json.dumps({
            "explicit_clean": "clean",
            "songwriters": "Jay Garrett",
            "copyright_year": "2026",
            "copyright_owner": "Jay Garrett",
            "isrc": "USRC17607839",
        }).encode("utf-8")
        status, data, _ = _request(
            port,
            "POST",
            "/api/release-record",
            body=save_body,
            headers={"Content-Type": "application/json"},
        )
        saved = json.loads(data.decode("utf-8"))
        assert status == 200
        saved_fields = {item["id"]: item for item in saved["fields"]}
        assert saved_fields["isrc"]["value"] == "USRC17607839"
        assert saved["release_readiness"] == "INCOMPLETE"

        status, data, _ = _request(port, "GET", "/api/release-record")
        reloaded = json.loads(data.decode("utf-8"))
        assert {item["id"]: item for item in reloaded["fields"]}["isrc"]["value"] == "USRC17607839"

        assert _request(
            port,
            "POST",
            "/api/approve",
            body=b'{"confirm": true}',
            headers={"Content-Type": "application/json"},
        )[0] == 200
        canonical = _request(port, "GET", "/export/approved_lyrics.txt")[1]
        status, data, _ = _request(port, "GET", "/api/release-record")
        after = json.loads(data.decode("utf-8"))
        after_fields = {item["id"]: item for item in after["fields"]}
        assert after_fields["approved_lyrics"]["status"] == "AVAILABLE"
        assert after["release_readiness"] == "READY"
        assert after_fields["track_number"]["status"] == "MISSING"
        assert _request(port, "GET", "/export/approved_lyrics.txt")[1] == canonical
        sheet = json.loads(_request(port, "GET", "/api/export")[1].decode("utf-8"))
        assert sheet["download_name"] == "Jay Garrett - Stomp To.txt"
        assert sheet["format"] == "standard-lyric-sheet"
        path = tmp_path / "artifacts" / "ingest" / app.job_id / "song_release_record.json"
        assert path.is_file()
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert stored["usable_as_approved_lyrics"] is False
        assert stored["not_a_release_or_distribution"] is True
    finally:
        server.shutdown()


def test_album_manifest_round_trip_and_live_song_truth(tmp_path: Path, monkeypatch) -> None:
    from a2l.ingest import ingest_wav
    from a2l.metadata import write_song_metadata
    from tests.wav_fixtures import write_pcm_wav

    app, server, port = _start(tmp_path, monkeypatch)
    try:
        session = json.loads(_request(port, "GET", "/api/session")[1].decode("utf-8"))
        assert session["can_album"] is True
        status, data, _ = _request(
            port,
            "POST",
            "/api/albums",
            body=json.dumps({"album_title": "Demo Album", "primary_artist": "Jay Garrett", "release_type": "album"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        created = json.loads(data.decode("utf-8"))
        assert status == 200
        assert created["album_title"] == "Demo Album"
        assert created["primary_artist"] == "Jay Garrett"
        assert created["release_type"] == "album"
        assert created["album_ready_determination"] is False
        assert created["summary"]["tracks"] == 0

        boundary, body = _multipart("demo.wav", pcm_wav_bytes(), song_title="Song A", artist="Jay Garrett")
        assert _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )[0] == 200
        session = _wait_ready(port)
        first_job = app.job_id
        assert session["error"] == ""
        assert first_job

        second_wav = write_pcm_wav(tmp_path / "other.wav", frame_count=8820)
        second = ingest_wav(second_wav, tmp_path / "artifacts")
        write_song_metadata(second.job_id, "Song B", "Jay Garrett", job_dir=second.artifact_dir)

        status, data, _ = _request(port, "GET", "/api/catalog-songs")
        catalog = json.loads(data.decode("utf-8"))
        assert status == 200
        ids = {item["ingest_job_id"] for item in catalog["songs"]}
        assert first_job in ids
        assert second.job_id in ids

        status, data, _ = _request(
            port,
            "POST",
            "/api/album",
            body=json.dumps({
                "id": created["release_id"],
                "album_title": "Demo Album",
                "primary_artist": "Jay Garrett",
                "release_type": "single",
                "track_ids": [second.job_id, first_job],
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        saved = json.loads(data.decode("utf-8"))
        assert status == 200
        assert saved["release_type"] == "single"
        assert [item["ingest_job_id"] for item in saved["tracks"]] == [second.job_id, first_job]
        assert saved["tracks"][0]["song_title"] == "Song B"
        assert saved["tracks"][1]["song_title"] == "Song A"
        assert saved["tracks"][0]["release_readiness"] == "INCOMPLETE"
        missing = {item["label"] for item in saved["tracks"][0]["missing_fields"]}
        assert "Songwriter(s)" in missing
        assert "ISRC" in missing

        status, data, _ = _request(port, "GET", f"/api/album?id={created['release_id']}")
        reloaded = json.loads(data.decode("utf-8"))
        assert status == 200
        assert [item["ingest_job_id"] for item in reloaded["tracks"]] == [second.job_id, first_job]

        status, data, _ = _request(
            port,
            "POST",
            "/api/open-song",
            body=json.dumps({"ingest_job_id": second.job_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        opened = json.loads(data.decode("utf-8"))
        assert status == 200
        assert app.job_id == second.job_id
        status, data, _ = _request(port, "GET", "/api/release-record")
        record = json.loads(data.decode("utf-8"))
        assert status == 200
        assert record["release_readiness"] == "INCOMPLETE"
        save_body = json.dumps({"songwriters": "Jay Garrett", "isrc": "USRC17607839"}).encode("utf-8")
        assert _request(port, "POST", "/api/release-record", body=save_body, headers={"Content-Type": "application/json"})[0] == 200
        status, data, _ = _request(port, "GET", f"/api/album?id={created['release_id']}")
        refreshed = json.loads(data.decode("utf-8"))
        refreshed_missing = {item["id"] for item in refreshed["tracks"][0]["missing_fields"]}
        assert "songwriters" not in refreshed_missing
        assert "isrc" not in refreshed_missing
        assert refreshed["tracks"][0]["release_readiness"] == "INCOMPLETE"
        assert "album_ready" not in refreshed
        assert refreshed["album_ready_determination"] is False

        status, data, _ = _request(
            port,
            "POST",
            "/api/album",
            body=json.dumps({
                "id": created["release_id"],
                "track_ids": [first_job],
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        after_remove = json.loads(data.decode("utf-8"))
        assert status == 200
        assert [item["ingest_job_id"] for item in after_remove["tracks"]] == [first_job]
        assert (second.artifact_dir / "ingest_manifest.json").is_file()
        assert (tmp_path / "artifacts" / "releases" / created["release_id"] / "album_release_manifest.json").is_file()

        status, data, _ = _request(port, "POST", "/api/album-readiness", body=json.dumps({"id": created["release_id"]}).encode("utf-8"), headers={"Content-Type": "application/json"})
        readiness = json.loads(data.decode("utf-8"))
        assert status == 200
        assert readiness["overall_state"] == "INCOMPLETE"
        assert readiness["assessment_type"] == "A2L_INTERNAL_RELEASE_READINESS"
        assert readiness["distributor_readiness"] is False
        assert any(item["id"] == "songwriters" and item["blocking"] is True for item in readiness["tracks"][0]["blocking_missing_fields"])
        assert any(item["id"] == "isrc" and item["blocking"] is False for item in readiness["tracks"][0]["optional_missing_fields"])
        assert (tmp_path / "artifacts" / "releases" / created["release_id"] / "album_release_readiness.json").is_file()
    finally:
        server.shutdown()


def test_app_html_hides_engineering_paths() -> None:
    html = (Path(__file__).resolve().parents[1] / "a2l" / "app.html").read_text(encoding="utf-8")
    assert "Upload" in html and "Processing" in html and "Review" in html
    assert "Approval" in html and "Output" in html
    assert "Release" in html
    assert "Album" in html
    assert "Album Release Manifest" in html
    assert "Song Release Record" in html
    assert "Create album" in html
    assert "Assess release readiness" in html
    assert "A2L INTERNAL RELEASE READINESS" in html
    assert "MISSING — BLOCKING" in html
    assert "MISSING — OPTIONAL" in html
    assert "ALBUM READY" not in html
    assert "DISTRIBUTION READY" not in html
    assert "STANDARD LYRIC SHEET" in html
    assert 'id="output-format"' in html
    assert "standard-lyric-sheet" in html
    assert "artifacts/ingest" not in html
    assert "python -m" not in html
    assert "confirm: true" in html
    assert 'id="engine"' in html
    assert "nvidia-parakeet" in html
    assert 'id="song-title"' in html
    assert 'id="artist"' in html
    assert 'id="review-song-title"' in html
    assert 'id="review-artist"' in html
    assert "The file name is not used as the title." in html
