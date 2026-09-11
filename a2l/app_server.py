"""A2L operator application (ACI-A2L-010).

Coordinates the validated pipeline. Does not replace transcription or approval rules.
"""

from __future__ import annotations

import json
import tempfile
import threading
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from a2l.approve import (
    approve_reviewed_lyrics,
    default_approved_json_path,
    default_approved_txt_path,
    lyric_display_state,
    reopen_approved_lyrics,
)
from a2l.engines import FasterWhisperEngine, TranscriptionEngine
from a2l.errors import ApprovalError, IngestionError, ReviewError
from a2l.ingest import ingest_wav
from a2l.pipeline import ROOT
from a2l.review import apply_corrections, load_or_create_review, save_review
from a2l.review_server import public_state
from a2l.structure import structure_lyrics
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import evaluate_uncertainty

UI_PATH = Path(__file__).with_name("app.html")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8780

STATUS_IDLE = "Choose a song to extract lyrics."
STATUS_READING = "Reading the song."
STATUS_EXTRACTING = "Extracting lyrics."
STATUS_CHECKING = "Checking uncertain phrases."
STATUS_PREPARING = "Preparing review."
STATUS_READY = "Ready to review."


class AppState:
    def __init__(
        self,
        artifact_root: Path | None = None,
        engine: TranscriptionEngine | None = None,
    ) -> None:
        self.artifact_root = Path(artifact_root) if artifact_root else ROOT / "artifacts"
        self.engine = engine
        self.lock = threading.Lock()
        self.filename = ""
        self.job_id = ""
        self.screen = "upload"
        self.status = STATUS_IDLE
        self.error = ""
        self.busy = False
        self.source_sha256 = ""

    def snapshot(self) -> dict:
        with self.lock:
            job = self.job_id
            filename = self.filename
            screen = self.screen
            status = self.status
            error = self.error
            busy = self.busy
        lyric_state = None
        can_export = False
        # Do not create review artifacts while extraction is writing them.
        if job and not busy and not error:
            try:
                review = load_or_create_review(sha=job)
                lyric_state = lyric_display_state(review, job)
                can_export = lyric_state == "APPROVED" and default_approved_txt_path(job).is_file()
            except ReviewError:
                lyric_state = None
        return {
            "ok": True,
            "filename": filename,
            "screen": screen,
            "status": status,
            "error": error,
            "busy": busy,
            "lyric_state": lyric_state,
            "can_review": bool(job) and not busy and not error,
            "can_approve": bool(job) and not busy and not error,
            "can_export": can_export,
            "has_job": bool(job),
        }

    def start_extract(self, filename: str, wav_bytes: bytes) -> dict:
        name = Path(filename or "song.wav").name
        if not name.lower().endswith(".wav"):
            return {"ok": False, "error_code": "NOT_WAV", "error": "Please choose a WAV file."}
        with self.lock:
            if self.busy:
                return {"ok": False, "error_code": "BUSY", "error": "Lyric extraction is already running."}
            self.busy = True
            self.filename = name
            self.error = ""
            self.status = STATUS_READING
            self.screen = "processing"
            self.job_id = ""
            self.source_sha256 = ""
        thread = threading.Thread(target=self._run_pipeline, args=(name, wav_bytes), daemon=True)
        thread.start()
        return {"ok": True, "status": STATUS_READING, "screen": "processing"}

    def _run_pipeline(self, filename: str, wav_bytes: bytes) -> None:
        tmp_dir = None
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="a2l-upload-"))
            wav_path = tmp_dir / name_safe(filename)
            wav_path.write_bytes(wav_bytes)
            ingest = ingest_wav(wav_path, self.artifact_root)
            with self.lock:
                self.status = STATUS_EXTRACTING
            transcribe_from_manifest(ingest.manifest_path, engine=self.engine or FasterWhisperEngine())
            with self.lock:
                self.status = STATUS_CHECKING
            draft_path = ingest.artifact_dir / "a2l_pipeline" / "machine_transcription" / "transcription_draft.json"
            uncertainty = evaluate_uncertainty(draft_path)
            with self.lock:
                self.status = STATUS_PREPARING
            structure_lyrics(uncertainty.report_path)
            load_or_create_review(sha=ingest.job_id)
            with self.lock:
                self.job_id = ingest.job_id
                self.source_sha256 = ingest.source_sha256
                self.status = STATUS_READY
                self.screen = "review"
                self.busy = False
                self.error = ""
        except IngestionError as exc:
            self._fail(operator_ingest_message(exc))
        except Exception:
            self._fail("Lyric extraction failed. The song file was not changed.")
        finally:
            if tmp_dir is not None:
                for path in tmp_dir.glob("*"):
                    try:
                        path.unlink()
                    except OSError:
                        pass
                try:
                    tmp_dir.rmdir()
                except OSError:
                    pass

    def _fail(self, message: str) -> None:
        with self.lock:
            self.busy = False
            self.job_id = ""
            self.source_sha256 = ""
            self.error = message
            self.status = message
            self.screen = "upload"


def name_safe(filename: str) -> str:
    name = Path(filename or "song.wav").name
    if not name.lower().endswith(".wav"):
        name = "song.wav"
    return name


def operator_ingest_message(exc: IngestionError) -> str:
    if exc.code in {"NOT_WAV", "UNSUPPORTED_FORMAT", "UNSUPPORTED_CODEC"}:
        return "Please choose a WAV file."
    if exc.code in {"CORRUPT_WAV", "EMPTY_INPUT", "EMPTY_AUDIO", "INVALID_WAV"}:
        return "That WAV file could not be read."
    return "That song file could not be used."


def operator_state(sha: str, review: dict) -> dict:
    state = public_state(sha, review)
    review_out = {
        "lines": review.get("lines") or [],
        "authority": review.get("authority"),
        "active_lyric_authority": review.get("active_lyric_authority"),
        "approval_status": review.get("approval_status"),
        "lyric_state": review.get("lyric_state"),
        "counts": review.get("counts"),
        "transcription_engine": review.get("transcription_engine"),
        "transcription_model": review.get("transcription_model"),
    }
    return {
        "ok": True,
        "review": review_out,
        "lyric_state": state["lyric_state"],
        "active_lyric_authority": state["active_lyric_authority"],
    }


def parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    if "multipart/form-data" not in (content_type or ""):
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    boundary = ""
    for part in content_type.split(";"):
        item = part.strip()
        if item.lower().startswith("boundary="):
            boundary = item.split("=", 1)[1].strip().strip('"')
    if not boundary:
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    marker = b"--" + boundary.encode("utf-8")
    start = body.find(marker)
    if start < 0:
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    rest = body[start + len(marker) :]
    if rest.startswith(b"--"):
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    if rest.startswith(b"\r\n"):
        rest = rest[2:]
    elif rest.startswith(b"\n"):
        rest = rest[1:]
    header_blob, separator, file_body = rest.partition(b"\r\n\r\n")
    if not separator:
        header_blob, separator, file_body = rest.partition(b"\n\n")
    if not separator:
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    headers = header_blob.decode("utf-8", errors="replace")
    if "filename=" not in headers.lower():
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    filename = "song.wav"
    for token in headers.replace("\r", "\n").split("\n"):
        if "filename=" in token.lower():
            raw = token.split("filename=", 1)[1].strip()
            if raw.startswith('"'):
                filename = raw.split('"', 2)[1]
            else:
                filename = raw.split(";", 1)[0].strip()
    end = file_body.find(b"\r\n" + marker)
    if end < 0:
        end = file_body.find(b"\n" + marker)
    payload = file_body[:end] if end >= 0 else file_body
    return Path(filename).name, payload


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, app: AppState, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[a2l] {self.address_string()} {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/app"):
            self._send(200, UI_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/session":
            self._send_json(200, self.app.snapshot())
            return
        if parsed.path == "/api/state":
            self._review_state()
            return
        if parsed.path in ("/export/lyrics.txt", "/export/approved_lyrics.txt"):
            self._export("txt")
            return
        if parsed.path in ("/export/lyrics.json", "/export/approved_lyrics.json"):
            self._export("json")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if parsed.path == "/api/extract":
            try:
                filename, wav_bytes = parse_multipart_file(self.headers.get("Content-Type") or "", body)
                result = self.app.start_extract(filename, wav_bytes)
            except IngestionError as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            status = 200 if result.get("ok") else 400
            self._send_json(status, result)
            return
        payload = json.loads(body.decode("utf-8") or "{}") if body else {}
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        if parsed.path == "/api/save":
            updates = {int(item["index"]): str(item.get("human_text", "")) for item in payload.get("lines") or []}
            try:
                review = load_or_create_review(sha=job)
                apply_corrections(review, updates)
                save_review(review, sha=job)
            except ReviewError as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, review))
            return
        if parsed.path == "/api/approve":
            try:
                review = load_or_create_review(sha=job)
                result = approve_reviewed_lyrics(review, job, confirm=payload.get("confirm") is True)
            except (ReviewError, ApprovalError) as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, result["review"]))
            return
        if parsed.path == "/api/reopen":
            try:
                review = load_or_create_review(sha=job)
                result = reopen_approved_lyrics(review, job, confirm=payload.get("confirm") is True)
            except (ReviewError, ApprovalError) as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, result["review"]))
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _review_state(self) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        try:
            review = load_or_create_review(sha=job)
        except ReviewError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, operator_state(job, review))

    def _export(self, kind: str) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        path = default_approved_txt_path(job) if kind == "txt" else default_approved_json_path(job)
        if not path.is_file():
            self._send_json(400, {"ok": False, "error_code": "NOT_APPROVED", "error": "Lyrics are not approved yet."})
            return
        data = path.read_bytes()
        name = "approved_lyrics.txt" if kind == "txt" else "approved_lyrics.json"
        content_type = "text/plain; charset=utf-8" if kind == "txt" else "application/json; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self._send(status, raw, "application/json; charset=utf-8")


def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    artifact_root: Path | None = None,
    engine: TranscriptionEngine | None = None,
    open_browser: bool = True,
) -> AppState:
    app = AppState(artifact_root=artifact_root, engine=engine)
    handler = partial(AppHandler, app=app)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print("A2L APPLICATION")
    print(url)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nA2L application stopped")
    finally:
        server.server_close()
    return app
