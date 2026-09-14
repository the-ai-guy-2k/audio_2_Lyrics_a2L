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
from urllib.parse import parse_qs, urlparse

from a2l.album_manifest import (
    create_album_manifest,
    detect_pipeline_dirname,
    list_album_manifests,
    list_catalog_songs,
    load_album_manifest,
    original_filename_for_song,
    public_album_payload,
    save_album_manifest,
)
from a2l.approve import (
    approve_reviewed_lyrics,
    default_approved_json_path,
    default_approved_txt_path,
    lyric_display_state,
    reopen_approved_lyrics,
)
from a2l.engines import FasterWhisperEngine, ParakeetEngine, TranscriptionEngine
from a2l.errors import ApprovalError, ExportError, IngestionError, ReleaseError, ReviewError, TranscriptionError
from a2l.export import (
    DEFAULT_FORMAT,
    content_disposition_attachment,
    format_approved_export,
    public_export_payload,
)
from a2l.ingest import ingest_wav
from a2l.metadata import apply_song_metadata, overlay_working_metadata, write_song_metadata
from a2l.release_record import (
    load_or_create_release_record,
    public_release_payload,
    save_release_record,
)
from a2l.pipeline import (
    ENGINE_ID_FASTER_WHISPER,
    ENGINE_ID_NVIDIA_PARAKEET,
    PIPELINE_DIRNAME,
    TRANSCRIPTION_DIRNAME,
    ROOT,
    pipeline_dirname_for_engine,
)
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
        self.pipeline_dirname = PIPELINE_DIRNAME
        self.engine_id = ENGINE_ID_FASTER_WHISPER
        self.transcription_seconds = None
        self.screen = "upload"
        self.status = STATUS_IDLE
        self.error = ""
        self.busy = False
        self.source_sha256 = ""
        self.song_title = None
        self.artist = None

    def snapshot(self) -> dict:
        with self.lock:
            job = self.job_id
            filename = self.filename
            screen = self.screen
            status = self.status
            error = self.error
            busy = self.busy
            dirname = self.pipeline_dirname
        lyric_state = None
        can_export = False
        song_title = None
        artist = None
        can_release = False
        release_readiness = None
        # Do not create review artifacts while extraction is writing them.
        if job and not busy and not error:
            can_release = True
            try:
                review = load_or_create_review(sha=job, pipeline_dirname=dirname)
                lyric_state = lyric_display_state(review, job)
                can_export = lyric_state == "APPROVED" and default_approved_txt_path(
                    job, pipeline_dirname=review.get("pipeline_dirname") or dirname
                ).is_file()
                song_title = review.get("song_title")
                artist = review.get("artist")
            except ReviewError:
                lyric_state = None
            try:
                record = load_or_create_release_record(
                    job,
                    pipeline_dirname=dirname,
                    artifact_root=self.artifact_root,
                    persist=False,
                )
                release_readiness = record.get("release_readiness")
            except (ReleaseError, ReviewError):
                release_readiness = None
        return {
            "ok": True,
            "filename": filename,
            "screen": screen,
            "status": status,
            "error": error,
            "busy": busy,
            "lyric_state": lyric_state,
            "song_title": song_title,
            "artist": artist,
            "can_review": bool(job) and not busy and not error,
            "can_approve": bool(job) and not busy and not error,
            "can_export": can_export,
            "can_release": can_release,
            "can_album": True,
            "release_readiness": release_readiness,
            "has_job": bool(job),
        }

    def start_extract(
        self,
        filename: str,
        wav_bytes: bytes,
        engine_id: str | None = None,
        song_title=None,
        artist=None,
    ) -> dict:
        name = Path(filename or "song.wav").name
        if not name.lower().endswith(".wav"):
            return {"ok": False, "error_code": "NOT_WAV", "error": "Please choose a WAV file."}
        selected = engine_id or ENGINE_ID_FASTER_WHISPER
        if selected not in {ENGINE_ID_FASTER_WHISPER, ENGINE_ID_NVIDIA_PARAKEET}:
            return {
                "ok": False,
                "error_code": "UNKNOWN_ENGINE",
                "error": "Choose FASTER-WHISPER or NVIDIA PARAKEET.",
            }
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
            self.engine_id = selected
            self.pipeline_dirname = PIPELINE_DIRNAME
            self.transcription_seconds = None
            self.song_title = song_title
            self.artist = artist
        thread = threading.Thread(
            target=self._run_pipeline,
            args=(name, wav_bytes, selected, song_title, artist),
            daemon=True,
        )
        thread.start()
        return {"ok": True, "status": STATUS_READING, "screen": "processing"}

    def _runtime_engine(self, engine_id: str) -> TranscriptionEngine:
        if self.engine is not None:
            return self.engine
        if engine_id == ENGINE_ID_NVIDIA_PARAKEET:
            return ParakeetEngine()
        return FasterWhisperEngine()

    def _run_pipeline(self, filename: str, wav_bytes: bytes, engine_id: str, song_title=None, artist=None) -> None:
        tmp_dir = None
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="a2l-upload-"))
            wav_path = tmp_dir / name_safe(filename)
            wav_path.write_bytes(wav_bytes)
            ingest = ingest_wav(wav_path, self.artifact_root)
            engine = self._runtime_engine(engine_id)
            dirname = pipeline_dirname_for_engine(engine)
            with self.lock:
                self.status = STATUS_EXTRACTING
                self.pipeline_dirname = dirname
            transcribed = transcribe_from_manifest(ingest.manifest_path, engine=engine)
            with self.lock:
                self.status = STATUS_CHECKING
                self.transcription_seconds = transcribed.draft.get("transcription_seconds")
            draft_path = ingest.artifact_dir / dirname / TRANSCRIPTION_DIRNAME / "transcription_draft.json"
            uncertainty = evaluate_uncertainty(draft_path)
            with self.lock:
                self.status = STATUS_PREPARING
            structure_lyrics(uncertainty.report_path)
            review = load_or_create_review(sha=ingest.job_id, pipeline_dirname=dirname)
            if lyric_display_state(review, ingest.job_id) != "APPROVED":
                write_song_metadata(ingest.job_id, song_title, artist, job_dir=ingest.artifact_dir)
                overlay_working_metadata(review, ingest.job_id, job_dir=ingest.artifact_dir)
            with self.lock:
                self.job_id = ingest.job_id
                self.source_sha256 = ingest.source_sha256
                self.pipeline_dirname = dirname
                self.status = STATUS_READY
                self.screen = "review"
                self.busy = False
                self.error = ""
        except IngestionError as exc:
            self._fail(operator_ingest_message(exc))
        except TranscriptionError as exc:
            if exc.code == "ENGINE_UNAVAILABLE":
                self._fail("That transcription engine is not available in this environment.")
            else:
                self._fail("Lyric extraction failed. The song file was not changed.")
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
        "pipeline_dirname": review.get("pipeline_dirname"),
        "song_title": review.get("song_title"),
        "artist": review.get("artist"),
    }
    return {
        "ok": True,
        "review": review_out,
        "lyric_state": state["lyric_state"],
        "active_lyric_authority": state["active_lyric_authority"],
    }


def parse_extract_upload(content_type: str, body: bytes) -> tuple[str, bytes, str, str | None, str | None]:
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
    filename = None
    payload = None
    engine_id = ENGINE_ID_FASTER_WHISPER
    song_title = None
    artist = None
    for raw in body.split(marker):
        part = raw.lstrip(b"\r\n")
        if not part or part == b"--" or part.startswith(b"--"):
            continue
        header_blob, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            header_blob, separator, content = part.partition(b"\n\n")
        if not separator:
            continue
        if content.endswith(b"\r\n"):
            content = content[:-2]
        elif content.endswith(b"\n"):
            content = content[:-1]
        headers = header_blob.decode("utf-8", errors="replace")
        headers_l = headers.lower()
        if "filename=" in headers_l:
            name = "song.wav"
            for token in headers.replace("\r", "\n").split("\n"):
                if "filename=" in token.lower():
                    raw_name = token.split("filename=", 1)[1].strip()
                    if raw_name.startswith('"'):
                        name = raw_name.split('"', 2)[1]
                    else:
                        name = raw_name.split(";", 1)[0].strip()
            filename = Path(name).name
            payload = content
            continue
        field = _multipart_field_name(headers)
        if field == "engine":
            engine_id = content.decode("utf-8", errors="replace").strip() or ENGINE_ID_FASTER_WHISPER
        elif field == "song_title":
            song_title = content.decode("utf-8", errors="replace")
        elif field == "artist":
            artist = content.decode("utf-8", errors="replace")
    if filename is None or payload is None:
        raise IngestionError("NOT_WAV", "Please choose a WAV file.")
    if engine_id not in {ENGINE_ID_FASTER_WHISPER, ENGINE_ID_NVIDIA_PARAKEET}:
        raise IngestionError("UNKNOWN_ENGINE", "Choose FASTER-WHISPER or NVIDIA PARAKEET.")
    return filename, payload, engine_id, song_title, artist


def _multipart_field_name(headers: str) -> str:
    for token in headers.replace("\r", "\n").split("\n"):
        lowered = token.lower()
        if "content-disposition:" in lowered and "name=" in lowered:
            raw = token.split("name=", 1)[1].strip()
            if raw.startswith('"'):
                return raw.split('"', 2)[1]
            return raw.split(";", 1)[0].strip()
    return ""


def parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    filename, payload, _engine_id, _song_title, _artist = parse_extract_upload(content_type, body)
    return filename, payload


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
        if parsed.path == "/api/export":
            self._formatted_export(parsed)
            return
        if parsed.path == "/api/release-record":
            self._release_record()
            return
        if parsed.path == "/api/albums":
            self._list_albums()
            return
        if parsed.path == "/api/album":
            self._get_album(parsed)
            return
        if parsed.path == "/api/catalog-songs":
            self._catalog_songs()
            return
        if parsed.path in ("/export/lyrics.txt", "/export/approved_lyrics.txt"):
            self._export("txt")
            return
        if parsed.path in ("/export/lyrics.json", "/export/approved_lyrics.json"):
            self._export("json")
            return
        if parsed.path in ("/export/output.txt", "/export/lyric-sheet.txt"):
            self._download_formatted(parsed)
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if parsed.path == "/api/extract":
            try:
                filename, wav_bytes, engine_id, song_title, artist = parse_extract_upload(
                    self.headers.get("Content-Type") or "", body
                )
                result = self.app.start_extract(
                    filename,
                    wav_bytes,
                    engine_id=engine_id,
                    song_title=song_title,
                    artist=artist,
                )
            except IngestionError as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            status = 200 if result.get("ok") else 400
            self._send_json(status, result)
            return
        payload = json.loads(body.decode("utf-8") or "{}") if body else {}
        if parsed.path == "/api/albums":
            self._create_album(payload)
            return
        if parsed.path == "/api/album":
            self._save_album(payload)
            return
        if parsed.path == "/api/open-song":
            self._open_song(payload)
            return
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        dirname = self.app.pipeline_dirname
        if parsed.path == "/api/save":
            updates = {int(item["index"]): str(item.get("human_text", "")) for item in payload.get("lines") or []}
            try:
                review = load_or_create_review(sha=job, pipeline_dirname=dirname)
                apply_corrections(review, updates)
                if "song_title" in payload or "artist" in payload:
                    apply_song_metadata(review, payload.get("song_title"), payload.get("artist"))
                save_review(review, sha=job)
            except ReviewError as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, review))
            return
        if parsed.path == "/api/approve":
            try:
                review = load_or_create_review(sha=job, pipeline_dirname=dirname)
                result = approve_reviewed_lyrics(review, job, confirm=payload.get("confirm") is True)
            except (ReviewError, ApprovalError) as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, result["review"]))
            return
        if parsed.path == "/api/reopen":
            try:
                review = load_or_create_review(sha=job, pipeline_dirname=dirname)
                result = reopen_approved_lyrics(review, job, confirm=payload.get("confirm") is True)
            except (ReviewError, ApprovalError) as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, operator_state(job, result["review"]))
            return
        if parsed.path == "/api/release-record":
            self._save_release_record(payload)
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _review_state(self) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        try:
            review = load_or_create_review(sha=job, pipeline_dirname=self.app.pipeline_dirname)
        except ReviewError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, operator_state(job, review))

    def _release_record(self) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        try:
            record = load_or_create_release_record(
                job,
                pipeline_dirname=self.app.pipeline_dirname,
                artifact_root=self.app.artifact_root,
            )
        except (ReleaseError, ReviewError) as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_release_payload(record))

    def _save_release_record(self, payload: dict) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        try:
            record = save_release_record(
                job,
                updates=payload,
                pipeline_dirname=self.app.pipeline_dirname,
                artifact_root=self.app.artifact_root,
            )
        except (ReleaseError, ReviewError) as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_release_payload(record))

    def _list_albums(self) -> None:
        albums = list_album_manifests(artifact_root=self.app.artifact_root)
        self._send_json(200, {"ok": True, "albums": albums})

    def _catalog_songs(self) -> None:
        songs = list_catalog_songs(artifact_root=self.app.artifact_root)
        self._send_json(200, {"ok": True, "songs": songs})

    def _get_album(self, parsed) -> None:
        release_id = (parse_qs(parsed.query).get("id") or [""])[0]
        if not release_id:
            self._send_json(400, {"ok": False, "error_code": "ALBUM_NOT_FOUND", "error": "That album could not be found."})
            return
        try:
            record = load_album_manifest(release_id, artifact_root=self.app.artifact_root)
        except ReleaseError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_album_payload(record))

    def _create_album(self, payload: dict) -> None:
        try:
            record = create_album_manifest(
                album_title=payload.get("album_title"),
                primary_artist=payload.get("primary_artist"),
                release_type=payload.get("release_type"),
                artifact_root=self.app.artifact_root,
            )
        except ReleaseError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_album_payload(record))

    def _save_album(self, payload: dict) -> None:
        release_id = payload.get("id") or payload.get("release_id")
        if not release_id:
            self._send_json(400, {"ok": False, "error_code": "ALBUM_NOT_FOUND", "error": "That album could not be found."})
            return
        try:
            record = save_album_manifest(
                str(release_id),
                updates=payload,
                artifact_root=self.app.artifact_root,
            )
        except ReleaseError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_album_payload(record))

    def _open_song(self, payload: dict) -> None:
        ingest_job_id = payload.get("ingest_job_id") or payload.get("id")
        try:
            filename = original_filename_for_song(str(ingest_job_id or ""), artifact_root=self.app.artifact_root)
            job = "".join(ch for ch in str(ingest_job_id or "") if ch.isalnum())
            job_dir = self.app.artifact_root / "ingest" / job
            dirname = detect_pipeline_dirname(job_dir)
        except ReleaseError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        with self.app.lock:
            self.app.job_id = job
            self.app.pipeline_dirname = dirname
            self.app.filename = filename
            self.app.error = ""
            self.app.busy = False
            self.app.screen = "release"
        self._send_json(200, self.app.snapshot())

    def _formatted_export(self, parsed) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        format_id = (parse_qs(parsed.query).get("format") or [DEFAULT_FORMAT])[0]
        try:
            result = format_approved_export(job, format_id, pipeline_dirname=self.app.pipeline_dirname)
        except ExportError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, public_export_payload(result))

    def _download_formatted(self, parsed) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        format_id = (parse_qs(parsed.query).get("format") or [DEFAULT_FORMAT])[0]
        try:
            result = format_approved_export(job, format_id, pipeline_dirname=self.app.pipeline_dirname)
        except ExportError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        data = result.text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", content_disposition_attachment(result.download_name))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _export(self, kind: str) -> None:
        job = self.app.job_id
        if not job:
            self._send_json(400, {"ok": False, "error_code": "NO_SONG", "error": "Choose a song first."})
            return
        path = (
            default_approved_txt_path(job, pipeline_dirname=self.app.pipeline_dirname)
            if kind == "txt"
            else default_approved_json_path(job, pipeline_dirname=self.app.pipeline_dirname)
        )
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
