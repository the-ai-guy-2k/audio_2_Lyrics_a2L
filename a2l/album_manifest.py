"""ACI-A2L-REL-002 album release manifest.

Organizes existing Song Release Records into an Operator-ordered album
view. Missing per-song data is flagged, not invented. This is not
album-level readiness or distribution.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from a2l.errors import ReleaseError
from a2l.ingest import MANIFEST_FILENAME
from a2l.metadata import normalize_field
from a2l.pipeline import PARAKEET_PIPELINE_DIRNAME, PIPELINE_DIRNAME, ROOT
from a2l.release_record import (
    INCOMPLETE,
    READY,
    RECORD_FILENAME,
    STATUS_MISSING,
    load_or_create_release_record,
)

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-REL-002"
AUTHORITY = "ALBUM_RELEASE_MANIFEST"
RELEASES_DIRNAME = "releases"
MANIFEST_FILENAME_ALBUM = "album_release_manifest.json"
RELEASE_TYPES = {
    "album": "Album",
    "ep": "EP",
    "single": "Single",
}
CURRENT_TRUTH_NOTE = (
    "Track title, artist, duration, Song Release Record status, approved-lyric "
    "availability, and missing fields are read from the current Song Release Record "
    "when this album is loaded. The album file stores membership and Operator order only."
)
PROVENANCE = {
    "album_title": "OPERATOR_ENTERED",
    "primary_artist": "OPERATOR_ENTERED",
    "release_type": "OPERATOR_ENTERED",
    "track_order": "OPERATOR_SELECTED",
}


def releases_root(artifact_root: str | Path | None = None) -> Path:
    root = Path(artifact_root) if artifact_root is not None else ROOT / "artifacts"
    return root / RELEASES_DIRNAME


def default_manifest_path(release_id: str, artifact_root: str | Path | None = None) -> Path:
    return releases_root(artifact_root) / _safe_release_id(release_id) / MANIFEST_FILENAME_ALBUM


def create_album_manifest(
    album_title=None,
    primary_artist=None,
    release_type=None,
    artifact_root: str | Path | None = None,
    now: str | None = None,
    release_id: str | None = None,
) -> dict:
    ident = _safe_release_id(release_id) if release_id else uuid.uuid4().hex
    stored = {
        "release_id": ident,
        "album_title": normalize_field(album_title),
        "primary_artist": normalize_field(primary_artist),
        "release_type": _normalize_release_type(release_type),
        "tracks": [],
        "created_at": None,
    }
    return _write_assembled(stored, artifact_root=artifact_root, now=now)


def save_album_manifest(
    release_id: str,
    updates: dict | None = None,
    artifact_root: str | Path | None = None,
    now: str | None = None,
) -> dict:
    stored = _read_stored(release_id, artifact_root)
    incoming = updates or {}
    if "album_title" in incoming:
        stored["album_title"] = normalize_field(incoming.get("album_title"))
    if "primary_artist" in incoming:
        stored["primary_artist"] = normalize_field(incoming.get("primary_artist"))
    if "release_type" in incoming:
        stored["release_type"] = _normalize_release_type(incoming.get("release_type"))
    if "track_ids" in incoming:
        stored["tracks"] = _ordered_track_refs(incoming.get("track_ids"), artifact_root)
    return _write_assembled(stored, artifact_root=artifact_root, now=now)


def add_album_track(release_id: str, ingest_job_id: str, artifact_root: str | Path | None = None, now: str | None = None) -> dict:
    stored = _read_stored(release_id, artifact_root)
    job = _require_ingested_song(ingest_job_id, artifact_root)
    existing = [item["ingest_job_id"] for item in stored["tracks"]]
    if job in existing:
        raise ReleaseError("TRACK_ALREADY_ON_ALBUM", "That song is already on this album.")
    stored["tracks"].append({"ingest_job_id": job, "position": len(stored["tracks"]) + 1})
    return _write_assembled(stored, artifact_root=artifact_root, now=now)


def remove_album_track(release_id: str, ingest_job_id: str, artifact_root: str | Path | None = None, now: str | None = None) -> dict:
    stored = _read_stored(release_id, artifact_root)
    job = _normalize_job_id(ingest_job_id)
    kept = [item for item in stored["tracks"] if item.get("ingest_job_id") != job]
    if len(kept) == len(stored["tracks"]):
        raise ReleaseError("TRACK_NOT_ON_ALBUM", "That song is not on this album.")
    stored["tracks"] = kept
    return _write_assembled(stored, artifact_root=artifact_root, now=now)


def load_album_manifest(release_id: str, artifact_root: str | Path | None = None, now: str | None = None) -> dict:
    stored = _read_stored(release_id, artifact_root)
    return _assemble(stored, artifact_root=artifact_root, now=now)


def list_album_manifests(artifact_root: str | Path | None = None) -> list[dict]:
    root = releases_root(artifact_root)
    if not root.is_dir():
        return []
    items = []
    for path in root.glob(f"*/{MANIFEST_FILENAME_ALBUM}"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        ident = payload.get("release_id") or path.parent.name
        items.append(
            {
                "release_id": ident,
                "album_title": payload.get("album_title"),
                "primary_artist": payload.get("primary_artist"),
                "release_type": payload.get("release_type"),
                "updated_at": payload.get("updated_at"),
            }
        )
    items.sort(key=lambda item: (item.get("updated_at") or "", item.get("release_id") or ""))
    return items


def list_catalog_songs(artifact_root: str | Path | None = None) -> list[dict]:
    ingest_root = _ingest_root(artifact_root)
    if not ingest_root.is_dir():
        return []
    songs = []
    for job_dir in sorted(ingest_root.iterdir()):
        if not job_dir.is_dir() or not (job_dir / MANIFEST_FILENAME).is_file():
            continue
        record = load_or_create_release_record(job_dir.name, job_dir=job_dir, artifact_root=artifact_root, persist=False)
        fields = _fields(record)
        missing = [
            {"id": item["id"], "label": item["label"], "status": STATUS_MISSING}
            for item in record.get("fields") or []
            if item.get("status") == STATUS_MISSING
        ]
        songs.append(
            {
                "ingest_job_id": job_dir.name,
                "song_title": fields["song_title"]["value"],
                "primary_artist": fields["primary_artist"]["value"],
                "track_duration_seconds": fields["track_duration"]["value"],
                "release_readiness": record.get("release_readiness") or INCOMPLETE,
                "approved_lyrics_status": fields["approved_lyrics"]["status"],
                "missing_fields": missing,
            }
        )
    return songs


def public_album_payload(record: dict) -> dict:
    return {
        "ok": True,
        "release_id": record["release_id"],
        "album_title": record["album_title"],
        "primary_artist": record["primary_artist"],
        "release_type": record["release_type"],
        "release_type_label": RELEASE_TYPES.get(record["release_type"] or "", ""),
        "tracks": record["tracks"],
        "summary": record["summary"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "album_ready_determination": False,
        "current_truth_note": record["current_truth_note"],
        "provenance": record["provenance"],
        "notes": record["notes"],
    }


def detect_pipeline_dirname(job_dir: Path) -> str:
    root = Path(job_dir)
    if (root / PIPELINE_DIRNAME / "human_review").is_dir():
        return PIPELINE_DIRNAME
    if (root / PARAKEET_PIPELINE_DIRNAME / "human_review").is_dir():
        return PARAKEET_PIPELINE_DIRNAME
    if (root / PIPELINE_DIRNAME).is_dir():
        return PIPELINE_DIRNAME
    if (root / PARAKEET_PIPELINE_DIRNAME).is_dir():
        return PARAKEET_PIPELINE_DIRNAME
    return PIPELINE_DIRNAME


def original_filename_for_song(ingest_job_id: str, artifact_root: str | Path | None = None) -> str:
    job = require_ingested_song(ingest_job_id, artifact_root)
    path = _ingest_root(artifact_root) / job / MANIFEST_FILENAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    name = payload.get("original_filename")
    return Path(str(name)).name if name else ""


def require_ingested_song(ingest_job_id: str, artifact_root: str | Path | None = None) -> str:
    return _require_ingested_song(ingest_job_id, artifact_root)


def _ingest_root(artifact_root: str | Path | None) -> Path:
    root = Path(artifact_root) if artifact_root is not None else ROOT / "artifacts"
    return root / "ingest"


def _safe_release_id(value: str) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isalnum())
    if not text:
        raise ReleaseError("INVALID_RELEASE_ID", "That album could not be found.")
    return text


def _normalize_job_id(value: str) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isalnum())
    if len(text) < 8:
        raise ReleaseError("SONG_NOT_FOUND", "Choose an existing A2L song.")
    return text


def _normalize_release_type(value) -> str | None:
    text = normalize_field(value)
    if text is None:
        return None
    key = text.lower()
    if key not in RELEASE_TYPES:
        raise ReleaseError("INVALID_RELEASE_TYPE", "Release type must be Album, EP, or Single, or left empty.")
    return key


def _require_ingested_song(ingest_job_id: str, artifact_root: str | Path | None) -> str:
    job = _normalize_job_id(ingest_job_id)
    path = _ingest_root(artifact_root) / job / MANIFEST_FILENAME
    if not path.is_file():
        raise ReleaseError("SONG_NOT_FOUND", "Choose an existing A2L song.")
    return job


def _ordered_track_refs(track_ids, artifact_root: str | Path | None) -> list[dict]:
    refs = []
    seen = set()
    for raw in track_ids or []:
        job = _require_ingested_song(str(raw), artifact_root)
        if job in seen:
            continue
        seen.add(job)
        refs.append({"ingest_job_id": job, "position": len(refs) + 1})
    return refs


def _read_stored(release_id: str, artifact_root: str | Path | None) -> dict:
    path = default_manifest_path(release_id, artifact_root)
    if not path.is_file():
        raise ReleaseError("ALBUM_NOT_FOUND", "That album could not be found.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseError("ALBUM_MANIFEST_INVALID", "album_release_manifest.json is not valid JSON.") from exc
    tracks = []
    for item in payload.get("tracks") or []:
        if not isinstance(item, dict):
            continue
        job = item.get("ingest_job_id")
        if not job:
            continue
        tracks.append({"ingest_job_id": str(job), "position": len(tracks) + 1})
    return {
        "release_id": payload.get("release_id") or path.parent.name,
        "album_title": payload.get("album_title"),
        "primary_artist": payload.get("primary_artist"),
        "release_type": payload.get("release_type"),
        "tracks": tracks,
        "created_at": payload.get("created_at"),
    }


def _write_assembled(stored: dict, artifact_root: str | Path | None, now: str | None) -> dict:
    record = _assemble(stored, artifact_root=artifact_root, now=now)
    path = default_manifest_path(record["release_id"], artifact_root)
    persisted = {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "album_ready_determination": False,
        "release_id": record["release_id"],
        "album_title": record["album_title"],
        "primary_artist": record["primary_artist"],
        "release_type": record["release_type"],
        "tracks": [{"ingest_job_id": item["ingest_job_id"], "position": item["position"]} for item in record["tracks"]],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "provenance": PROVENANCE,
        "notes": record["notes"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(persisted, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return record


def _assemble(stored: dict, artifact_root: str | Path | None, now: str | None) -> dict:
    stamp = now or datetime.now(timezone.utc).isoformat()
    created = stored.get("created_at") or stamp
    tracks = []
    ready = 0
    incomplete = 0
    for index, item in enumerate(stored.get("tracks") or [], start=1):
        view = _live_track_view(item.get("ingest_job_id"), index, artifact_root)
        tracks.append(view)
        if view["release_readiness"] == READY:
            ready += 1
        else:
            incomplete += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "album_ready_determination": False,
        "release_id": stored["release_id"],
        "album_title": stored.get("album_title"),
        "primary_artist": stored.get("primary_artist"),
        "release_type": stored.get("release_type"),
        "tracks": tracks,
        "summary": {
            "tracks": len(tracks),
            "song_records_ready": ready,
            "song_records_incomplete": incomplete,
        },
        "created_at": created,
        "updated_at": stamp,
        "current_truth_note": CURRENT_TRUTH_NOTE,
        "provenance": PROVENANCE,
        "notes": [
            "Album Release Manifest. Organizes existing Song Release Records.",
            "Missing per-song information is not invented.",
            "Album title, artist, and type are Operator-entered. They are not inferred from filenames or track count.",
            "Track order is Operator-selected, not filesystem or ingestion order.",
            "This is not album-level READY, distribution READY, or a commercial release.",
            "Removing a track from the album does not delete the underlying song artifacts.",
        ],
    }


def _live_track_view(ingest_job_id: str, position: int, artifact_root: str | Path | None) -> dict:
    job = str(ingest_job_id or "")
    job_dir = _ingest_root(artifact_root) / job
    record_ref = f"ingest/{job}/{RECORD_FILENAME}"
    if not (job_dir / MANIFEST_FILENAME).is_file():
        return {
            "position": position,
            "ingest_job_id": job,
            "song_title": None,
            "primary_artist": None,
            "track_duration_seconds": None,
            "song_release_record_ref": record_ref,
            "release_readiness": INCOMPLETE,
            "approved_lyrics_status": STATUS_MISSING,
            "missing_fields": [],
            "song_present": False,
            "source": "SONG_RELEASE_RECORD",
        }
    record = load_or_create_release_record(job, job_dir=job_dir, artifact_root=artifact_root, persist=False)
    fields = _fields(record)
    missing = [
        {"id": item["id"], "label": item["label"], "status": STATUS_MISSING}
        for item in record.get("fields") or []
        if item.get("status") == STATUS_MISSING
    ]
    return {
        "position": position,
        "ingest_job_id": job,
        "song_title": fields["song_title"]["value"],
        "primary_artist": fields["primary_artist"]["value"],
        "track_duration_seconds": fields["track_duration"]["value"],
        "song_release_record_ref": record_ref,
        "release_readiness": record.get("release_readiness") or INCOMPLETE,
        "approved_lyrics_status": fields["approved_lyrics"]["status"],
        "missing_fields": missing,
        "song_present": True,
        "source": "SONG_RELEASE_RECORD",
    }


def _fields(record: dict) -> dict:
    empty = {"value": None, "status": STATUS_MISSING}
    by_id = {item["id"]: item for item in record.get("fields") or [] if item.get("id")}
    return {
        "song_title": by_id.get("song_title", empty),
        "primary_artist": by_id.get("primary_artist", empty),
        "track_duration": by_id.get("track_duration", empty),
        "approved_lyrics": by_id.get("approved_lyrics", empty),
    }
