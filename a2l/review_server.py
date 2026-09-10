"""Local human-review interface for ACI-A2L-006.

Stdlib HTTP server. No visual polish. Not an approval workflow.
"""

from __future__ import annotations

import json
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from a2l.errors import ReviewError
from a2l.faster_whisper_draft import LOCKED_SHA256
from a2l.review import apply_corrections, load_or_create_review, save_review

UI_PATH = Path(__file__).with_name("review.html")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class ReviewHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, sha: str = LOCKED_SHA256, **kwargs):
        self.sha = sha
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[review] {self.address_string()} {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, UI_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/state":
            try:
                state = load_or_create_review(sha=self.sha)
            except ReviewError as exc:
                self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
                return
            self._send_json(200, {"ok": True, "review": state})
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/save":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        updates = {int(item["index"]): str(item.get("human_text", "")) for item in payload.get("lines") or []}
        try:
            review = load_or_create_review(sha=self.sha)
            apply_corrections(review, updates)
            saved = save_review(review, sha=self.sha)
        except ReviewError as exc:
            self._send_json(400, {"ok": False, "error_code": exc.code, "error": exc.message})
            return
        self._send_json(200, {"ok": True, "saved_path": str(saved), "review": review})

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, sha: str = LOCKED_SHA256, open_browser: bool = True) -> None:
    load_or_create_review(sha=sha)
    handler = partial(ReviewHandler, sha=sha)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"HOW THE OPERATOR OPENS THE HUMAN REVIEW INTERFACE")
    print(f"{url}")
    print("python -m a2l review")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nreview server stopped")
    finally:
        server.server_close()
