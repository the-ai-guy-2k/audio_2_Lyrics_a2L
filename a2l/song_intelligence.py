"""ACI-A2L-SI-011/012 Song Intelligence product orchestration.

Analyzer thresholds and engines are not changed. Instrumentation
remains PARTIAL. After analysis, the governed Song Intelligence
Record is the combined data source. Temporary UI aggregation is a
derived cache and does not outrank the record.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from a2l.album_manifest import detect_pipeline_dirname, list_catalog_songs, require_ingested_song
from a2l.approve import AUTHORITY as APPROVED_LYRIC_AUTHORITY
from a2l.errors import ReleaseError, ReviewError, SongIntelligenceError
from a2l.ingest import MANIFEST_FILENAME, SOURCE_FILENAME, WORKING_FILENAME
from a2l.metadata import normalize_field
from a2l.pipeline import PIPELINE_DIRNAME
from a2l.release_record import load_or_create_release_record
from a2l.song_intelligence_engines import ENGINE_CATALOG, default_runners
from a2l.song_intelligence_record import (
    RECORD_TYPE,
    display_payload_from_sir,
    load_sir,
    persist_sir_from_run,
)

PRODUCER_ACI = "ACI-A2L-SI-012"
AGGREGATION_KIND = "TEMPORARY_UI_AGGREGATION"
UI_DIRNAME = "song_intelligence_ui"
AGGREGATION_FILENAME = "ui_aggregation.json"
DEFAULT_CAPABILITY = "full_song_intelligence"
STATUS_WAITING = "Waiting"
STATUS_RUNNING = "Running"
STATUS_COMPLETE = "Complete"
STATUS_PARTIAL = "Partial"
STATUS_UNAVAILABLE = "Unavailable"
STATUS_FAILED = "Failed"
STATUS_NOT_RUN = "Not run"

CAPABILITIES = {
    "full_song_intelligence": {
        "id": "full_song_intelligence",
        "label": "Full Song Intelligence",
        "engines": (
            "lyrics_workflow",
            "rhythm_structure",
            "key_mode",
            "clap_audio",
            "ast_genre",
            "panns_instrumentation",
            "lyric_intelligence",
        ),
    },
    "lyrics": {
        "id": "lyrics",
        "label": "Lyrics",
        "engines": ("lyrics_workflow",),
    },
    "rhythm_structure": {
        "id": "rhythm_structure",
        "label": "Rhythm + Structure",
        "engines": ("rhythm_structure",),
    },
    "key_mode": {
        "id": "key_mode",
        "label": "Key + Mode",
        "engines": ("key_mode",),
    },
    "audio_intelligence": {
        "id": "audio_intelligence",
        "label": "Audio Intelligence",
        "engines": ("clap_audio", "ast_genre", "panns_instrumentation"),
    },
    "lyric_intelligence": {
        "id": "lyric_intelligence",
        "label": "Lyric Intelligence",
        "engines": ("lyric_intelligence",),
    },
}

OUTPUT_GROUPS = (
    {"id": "song", "label": "Song"},
    {"id": "lyrics", "label": "Lyrics"},
    {"id": "music", "label": "Music Analysis"},
    {"id": "sound", "label": "Audio / Sound Analysis"},
    {"id": "meaning", "label": "Lyric Meaning"},
    {"id": "provenance", "label": "Provenance / Authority"},
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_engines(capability: str, advanced: list[str] | None = None) -> list[str]:
    spec = CAPABILITIES.get(capability)
    if spec is None:
        raise SongIntelligenceError("UNKNOWN_CAPABILITY", "Choose a Song Intelligence analysis.")
    allowed = list(spec["engines"])
    selected = [item for item in (advanced or []) if item]
    if not selected:
        return allowed
    unknown = [item for item in selected if item not in ENGINE_CATALOG]
    if unknown:
        raise SongIntelligenceError("UNKNOWN_ENGINE", "Choose an available analysis engine.")
    constrained = [item for item in allowed if item in selected]
    if not constrained:
        raise SongIntelligenceError(
            "ENGINE_NOT_IN_CAPABILITY",
            "Advanced engines must belong to the selected analysis.",
        )
    return constrained


def catalog_payload(artifact_root: Path | None = None) -> dict:
    songs = []
    for item in list_catalog_songs(artifact_root=artifact_root):
        title = item.get("song_title") or "Title not entered"
        artist = item.get("primary_artist") or "Artist not entered"
        duration = item.get("track_duration_seconds")
        songs.append(
            {
                "ingest_job_id": item["ingest_job_id"],
                "label": f"{title} — {artist}",
                "song_title": item.get("song_title"),
                "artist": item.get("primary_artist"),
                "duration_seconds": duration,
                "approved_lyrics_status": item.get("approved_lyrics_status"),
            }
        )
    return {
        "ok": True,
        "default_capability": DEFAULT_CAPABILITY,
        "capabilities": [
            {"id": item["id"], "label": item["label"]} for item in CAPABILITIES.values()
        ],
        "engines": [
            {
                "id": engine_id,
                "label": spec["label"],
                "technical": spec["technical"],
                "produces": list(spec["produces"]),
            }
            for engine_id, spec in ENGINE_CATALOG.items()
        ],
        "output_groups": list(OUTPUT_GROUPS),
        "songs": songs,
    }


def public_payload(record: dict | None) -> dict:
    if not record:
        return {
            "ok": True,
            "available": False,
            "busy": False,
            "status": "Choose a song, then analyze.",
            "kind": RECORD_TYPE,
            "song_intelligence_record": False,
        }
    if record.get("record_type") == RECORD_TYPE:
        return display_payload_from_sir(record)
    aggregation = {
        "ok": True,
        "available": True,
        "busy": record.get("status") == STATUS_RUNNING,
        "kind": record.get("kind") or AGGREGATION_KIND,
        "song_intelligence_record": False,
        "usable_as_song_facts": False,
        "producer_aci": record.get("producer_aci") or PRODUCER_ACI,
        "status": record.get("status"),
        "current_engine": record.get("current_engine"),
        "capability": record.get("capability"),
        "engines_requested": record.get("engines_requested") or [],
        "modules": record.get("modules") or [],
        "groups": record.get("groups") or {},
        "fields": record.get("fields") or [],
        "song": record.get("song") or {},
        "error": record.get("error") or "",
        "analysis_seconds": record.get("analysis_seconds"),
        "peak_memory_bytes": record.get("peak_memory_bytes"),
        "master_hash_unchanged": record.get("master_hash_unchanged"),
        "notes": record.get("notes") or [],
        "governed_record_ref": record.get("governed_record_ref"),
    }
    return aggregation


def load_song_context(ingest_job_id: str, artifact_root: Path) -> dict:
    job = require_ingested_song(ingest_job_id, artifact_root)
    job_dir = Path(artifact_root) / "ingest" / job
    dirname = detect_pipeline_dirname(job_dir)
    manifest_path = job_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise SongIntelligenceError("SONG_NOT_FOUND", "Choose an existing A2L song.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SongIntelligenceError("SONG_NOT_FOUND", "Choose an existing A2L song.") from exc
    source_path = job_dir / "authoritative_source" / SOURCE_FILENAME
    working_path = job_dir / "derived_working" / WORKING_FILENAME
    if not working_path.is_file():
        raise SongIntelligenceError("WORKING_AUDIO_MISSING", "That song has no working audio copy.")
    title = None
    artist = None
    duration = (manifest.get("audio_metadata") or {}).get("duration_seconds")
    try:
        record = load_or_create_release_record(
            job, pipeline_dirname=dirname, job_dir=job_dir, artifact_root=artifact_root, persist=False
        )
        fields = {item["id"]: item for item in record.get("fields") or []}
        title = (fields.get("song_title") or {}).get("value")
        artist = (fields.get("primary_artist") or {}).get("value")
        if (fields.get("track_duration") or {}).get("value") is not None:
            duration = fields["track_duration"]["value"]
    except (ReleaseError, ReviewError):
        pass
    approved = _approved_lyrics(job, dirname, job_dir)
    return {
        "ingest_job_id": job,
        "job_dir": job_dir,
        "pipeline_dirname": dirname,
        "source_path": source_path,
        "working_path": working_path,
        "source_sha256": sha256_file(source_path) if source_path.is_file() else None,
        "working_sha256": sha256_file(working_path),
        "song_title": normalize_field(title),
        "artist": normalize_field(artist),
        "duration_seconds": duration,
        "approved_lyrics": approved,
        "ui_dir": job_dir / UI_DIRNAME,
    }


def _approved_lyrics(job: str, dirname: str, job_dir: Path) -> dict | None:
    folder = Path(job_dir) / (dirname or PIPELINE_DIRNAME) / "approved_lyrics"
    txt_path = folder / "approved_lyrics.txt"
    json_path = folder / "approved_lyrics.json"
    if not txt_path.is_file() or not json_path.is_file():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("authority") != APPROVED_LYRIC_AUTHORITY:
        return None
    if payload.get("approval_status") != "APPROVED" or payload.get("usable_as_approved_lyrics") is not True:
        return None
    text = txt_path.read_text(encoding="utf-8")
    json_text = payload.get("approved_lyric_text")
    if json_text is not None and json_text.replace("\r\n", "\n") != text.replace("\r\n", "\n"):
        return None
    event = payload.get("approval_event") or {}
    return {
        "text": text.replace("\r\n", "\n"),
        "authority": payload.get("authority") or APPROVED_LYRIC_AUTHORITY,
        "approval_status": payload.get("approval_status"),
        "revision": event.get("revision"),
        "usable_as_approved_lyrics": True,
    }


def empty_run(capability: str, engines: list[str], song: dict) -> dict:
    modules = []
    for engine_id in engines:
        spec = ENGINE_CATALOG[engine_id]
        modules.append(
            {
                "id": engine_id,
                "label": spec["label"],
                "technical": spec["technical"],
                "status": STATUS_WAITING,
                "message": "",
            }
        )
    return {
        "kind": AGGREGATION_KIND,
        "authority": None,
        "usable_as_song_facts": False,
        "song_intelligence_record": False,
        "producer_aci": PRODUCER_ACI,
        "ingest_job_id": song.get("ingest_job_id"),
        "status": STATUS_WAITING,
        "current_engine": None,
        "capability": capability,
        "engines_requested": list(engines),
        "modules": modules,
        "groups": {item["id"]: {"id": item["id"], "label": item["label"], "visible": True} for item in OUTPUT_GROUPS},
        "fields": song_identity_fields(song),
        "song": {
            "title": song.get("song_title"),
            "artist": song.get("artist"),
            "duration_seconds": song.get("duration_seconds"),
        },
        "error": "",
        "notes": [
            "This display is a temporary derived aggregation while analysis is running.",
            "After analysis completes, the governed Song Intelligence Record is the combined data source.",
            "Machine-derived values are not human-approved.",
        ],
        "started_at": None,
        "finished_at": None,
        "analysis_seconds": None,
        "peak_memory_bytes": None,
        "master_hash_unchanged": None,
    }


def song_identity_fields(song: dict) -> list[dict]:
    duration = song.get("duration_seconds")
    duration_text = f"{duration:.3f} s" if isinstance(duration, (int, float)) else None
    return [
        _field(
            "title",
            "song",
            "Title",
            song.get("song_title") or "Title not entered",
            engine_id="song_identity",
            engine_label="Song identity",
            engine_technical="Operator-entered metadata on the governed A2L song",
            authority="AUTHORITATIVE INPUT" if song.get("song_title") else "MISSING",
            status=STATUS_COMPLETE if song.get("song_title") else STATUS_UNAVAILABLE,
            validation_state="",
        ),
        _field(
            "artist",
            "song",
            "Artist",
            song.get("artist") or "Artist not entered",
            engine_id="song_identity",
            engine_label="Song identity",
            engine_technical="Operator-entered metadata on the governed A2L song",
            authority="AUTHORITATIVE INPUT" if song.get("artist") else "MISSING",
            status=STATUS_COMPLETE if song.get("artist") else STATUS_UNAVAILABLE,
            validation_state="",
        ),
        _field(
            "duration",
            "song",
            "Duration",
            duration_text or "unavailable",
            engine_id="song_identity",
            engine_label="Song identity",
            engine_technical="Measured from the ingested WAV",
            authority="MEASURED" if duration_text else "MISSING",
            status=STATUS_COMPLETE if duration_text else STATUS_UNAVAILABLE,
            validation_state="",
        ),
    ]


def _field(
    field_id: str,
    group: str,
    label: str,
    value,
    *,
    engine_id: str,
    engine_label: str,
    engine_technical: str,
    authority: str,
    status: str,
    validation_state: str = "PENDING HUMAN VALIDATION",
    evidence=None,
    note: str | None = None,
) -> dict:
    return {
        "id": field_id,
        "group": group,
        "label": label,
        "value": value,
        "engine_id": engine_id,
        "engine_label": engine_label,
        "engine_technical": engine_technical,
        "authority": authority,
        "status": status,
        "validation_state": validation_state,
        "evidence": evidence or [],
        "note": note or "",
    }


def persist_run(song: dict, record: dict, sir: dict | None = None) -> Path:
    ui_dir = song["ui_dir"]
    ui_dir.mkdir(parents=True, exist_ok=True)
    path = ui_dir / AGGREGATION_FILENAME
    aggregation = json.loads(json.dumps(record))
    aggregation["kind"] = AGGREGATION_KIND
    aggregation["song_intelligence_record"] = False
    aggregation["usable_as_song_facts"] = False
    aggregation["outranks_sir"] = False
    if sir:
        aggregation["governed_record_ref"] = f"ingest/{song['ingest_job_id']}/song_intelligence_record.json"
        aggregation["governed_revision"] = sir.get("revision")
        aggregation["notes"] = [
            "This file is a derived UI cache.",
            "It does not outrank the governed Song Intelligence Record.",
            f"Governed record: ingest/{song['ingest_job_id']}/song_intelligence_record.json",
        ]
    path.write_text(json.dumps(aggregation, indent=2) + "\n", encoding="utf-8")
    return path


def run_analysis(
    ingest_job_id: str,
    capability: str,
    advanced: list[str] | None,
    artifact_root: Path,
    runners: dict | None = None,
    on_update=None,
) -> dict:
    engines = resolve_engines(capability, advanced)
    song = load_song_context(ingest_job_id, artifact_root)
    record = empty_run(capability, engines, song)
    record["status"] = STATUS_RUNNING
    record["started_at"] = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    source_before = song.get("source_sha256")
    peak_memory = _working_set_bytes()
    execute = runners or default_runners()
    _emit(on_update, record)

    for index, engine_id in enumerate(engines):
        record["current_engine"] = ENGINE_CATALOG[engine_id]["label"]
        record["modules"][index]["status"] = STATUS_RUNNING
        _emit(on_update, record)
        runner = execute.get(engine_id)
        try:
            if runner is None:
                raise SongIntelligenceError("ENGINE_UNAVAILABLE", "That analysis engine is not available.")
            result = runner(song)
        except Exception as exc:
            result = {
                "status": STATUS_FAILED,
                "message": "That analysis engine failed. Other results were kept.",
                "fields": [],
                "error": f"{type(exc).__name__}",
            }
        status = result.get("status") or STATUS_FAILED
        record["modules"][index]["status"] = status
        record["modules"][index]["message"] = result.get("message") or ""
        record["modules"][index]["result_origin"] = result.get("result_origin") or "GENERATED"
        record["modules"][index]["source_artifact_ref"] = result.get("source_artifact_ref")
        record["fields"].extend(result.get("fields") or [])
        peak_memory = _max_memory(peak_memory, _working_set_bytes())
        _emit(on_update, record)

    source_after = sha256_file(song["source_path"]) if song["source_path"].is_file() else None
    record["current_engine"] = None
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["analysis_seconds"] = time.perf_counter() - started
    record["peak_memory_bytes"] = peak_memory
    record["master_hash_unchanged"] = bool(source_before and source_before == source_after)
    record["status"] = _overall_status(record["modules"])
    sir = persist_sir_from_run(song, record)
    persist_run(song, record, sir=sir)
    display = display_payload_from_sir(sir)
    display["busy"] = False
    _emit(on_update, display)
    return display


def _overall_status(modules: list[dict]) -> str:
    states = [item.get("status") for item in modules]
    if states and all(item == STATUS_FAILED for item in states):
        return STATUS_FAILED
    if any(item == STATUS_FAILED for item in states) or any(item == STATUS_PARTIAL for item in states) or any(
        item == STATUS_UNAVAILABLE for item in states
    ):
        if any(item in {STATUS_COMPLETE, STATUS_PARTIAL} for item in states):
            return STATUS_PARTIAL
        return STATUS_FAILED if any(item == STATUS_FAILED for item in states) else STATUS_UNAVAILABLE
    return STATUS_COMPLETE


def _emit(on_update, record: dict) -> None:
    if on_update is not None:
        on_update(json.loads(json.dumps(record)))


def _working_set_bytes():
    if __import__("sys").platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        return int(counters.WorkingSetSize) or None
    except Exception:
        return None


def _max_memory(left, right):
    values = [item for item in (left, right) if item is not None]
    return max(values) if values else None


class SongIntelligenceController:
    """Background sequential analysis for the operator application."""

    def __init__(self, artifact_root: Path, runners: dict | None = None) -> None:
        self.artifact_root = Path(artifact_root)
        self.runners = runners
        self.lock = threading.Lock()
        self.busy = False
        self.record: dict | None = None
        self.error = ""

    def snapshot(self, ingest_job_id: str | None = None) -> dict:
        with self.lock:
            record = json.loads(json.dumps(self.record)) if self.record else None
            busy = self.busy
            error = self.error
        if busy:
            payload = public_payload(record)
            payload["busy"] = True
            if error and not payload.get("error"):
                payload["error"] = error
            return payload
        job = ingest_job_id or (record or {}).get("ingest_job_id")
        if job:
            try:
                stored = load_sir(job, artifact_root=self.artifact_root)
            except SongIntelligenceError:
                stored = None
            if stored:
                payload = display_payload_from_sir(stored)
                payload["busy"] = False
                if error and not payload.get("error"):
                    payload["error"] = error
                return payload
        payload = public_payload(record)
        payload["busy"] = False
        if error and not payload.get("error"):
            payload["error"] = error
        return payload

    def start(self, ingest_job_id: str, capability: str | None, advanced: list[str] | None) -> dict:
        chosen = capability or DEFAULT_CAPABILITY
        engines = resolve_engines(chosen, advanced)
        song = load_song_context(ingest_job_id, self.artifact_root)
        with self.lock:
            if self.busy:
                raise SongIntelligenceError("BUSY", "Song Intelligence analysis is already running.")
            self.busy = True
            self.error = ""
            self.record = empty_run(chosen, engines, song)
            self.record["status"] = STATUS_RUNNING
        thread = threading.Thread(
            target=self._run,
            args=(ingest_job_id, chosen, advanced),
            daemon=True,
        )
        thread.start()
        return self.snapshot()

    def _run(self, ingest_job_id: str, capability: str, advanced: list[str] | None) -> None:
        def on_update(record: dict) -> None:
            with self.lock:
                self.record = record

        try:
            record = run_analysis(
                ingest_job_id,
                capability,
                advanced,
                self.artifact_root,
                runners=self.runners,
                on_update=on_update,
            )
            with self.lock:
                self.record = record
                self.busy = False
                self.error = ""
        except SongIntelligenceError as exc:
            with self.lock:
                self.busy = False
                self.error = exc.message
                if self.record is not None:
                    self.record["status"] = STATUS_FAILED
                    self.record["error"] = exc.message
        except Exception:
            with self.lock:
                self.busy = False
                self.error = "Song Intelligence analysis failed. The song file was not changed."
                if self.record is not None:
                    self.record["status"] = STATUS_FAILED
                    self.record["error"] = self.error
