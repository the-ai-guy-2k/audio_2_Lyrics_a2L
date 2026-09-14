"""ACI-A2L-REL-003 album release readiness.

Deterministic A2L INTERNAL RELEASE READINESS from the Album Release
Manifest and current Song Release Records. Missing data is flagged,
not invented. This is not distributor, store, or commercial readiness.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from a2l.album_manifest import default_manifest_path, load_album_manifest
from a2l.metadata import normalize_field
from a2l.release_record import (
    FIELD_LABELS,
    INCOMPLETE,
    READY,
    REQUIRED_FOR_READY,
    STATUS_AVAILABLE,
    STATUS_MISSING,
    load_or_create_release_record,
)

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-REL-003"
AUTHORITY = "A2L_INTERNAL_READINESS_ASSESSMENT"
ASSESSMENT_TYPE = "A2L_INTERNAL_RELEASE_READINESS"
READINESS_FILENAME = "album_release_readiness.json"
RULES_VERSION = "REL-001-song+REL-003-album"
READINESS_NOTE = (
    "READY means this album satisfies A2L internal release-information completeness. "
    "It does not mean the album has been commercially released, accepted by a distributor, "
    "delivered to a store, or legally registered."
)
ALBUM_REQUIRED = (
    ("album_title", "Album Title"),
    ("primary_artist", "Primary Artist"),
    ("release_type", "Release Type"),
)


def default_readiness_path(release_id: str, artifact_root: str | Path | None = None) -> Path:
    return default_manifest_path(release_id, artifact_root).with_name(READINESS_FILENAME)


def assess_album_readiness(
    release_id: str,
    artifact_root: str | Path | None = None,
    now: str | None = None,
    persist: bool = True,
) -> dict:
    album = load_album_manifest(release_id, artifact_root=artifact_root, now=now)
    stamp = now or datetime.now(timezone.utc).isoformat()
    album_fields, missing_album = _album_required_results(album)
    tracks = [_track_assessment(item, artifact_root) for item in album.get("tracks") or []]
    ready_tracks = sum(1 for item in tracks if item["release_readiness"] == READY)
    incomplete_tracks = len(tracks) - ready_tracks
    overall = READY if not missing_album and tracks and incomplete_tracks == 0 else INCOMPLETE
    record = {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "assessment_type": ASSESSMENT_TYPE,
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_readiness": False,
        "release_id": album["release_id"],
        "album_title": album.get("album_title"),
        "primary_artist": album.get("primary_artist"),
        "release_type": album.get("release_type"),
        "overall_state": overall,
        "readiness_note": READINESS_NOTE,
        "album_fields": album_fields,
        "missing_album_fields": missing_album,
        "summary": {
            "tracks": len(tracks),
            "ready_tracks": ready_tracks,
            "incomplete_tracks": incomplete_tracks,
        },
        "tracks": tracks,
        "album_manifest_ref": f"releases/{album['release_id']}/album_release_manifest.json",
        "assessed_at": stamp,
        "rules_version": RULES_VERSION,
        "current_truth_note": (
            "This assessment reads the current Album Release Manifest and current Song "
            "Release Records. It does not freeze per-song values as a second authority."
        ),
        "notes": [
            "A2L INTERNAL RELEASE READINESS assessment.",
            "READY is internal completeness, not commercial or distributor readiness.",
            "Missing information is flagged. Values are not invented.",
            "Optional Song Release Record fields do not block internal READY.",
            "Track membership and order remain owned by the Album Release Manifest.",
        ],
    }
    if persist:
        path = default_readiness_path(album["release_id"], artifact_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return record


def public_readiness_payload(record: dict) -> dict:
    return {
        "ok": True,
        "release_id": record["release_id"],
        "album_title": record["album_title"],
        "primary_artist": record["primary_artist"],
        "release_type": record["release_type"],
        "assessment_type": record["assessment_type"],
        "authority": record["authority"],
        "overall_state": record["overall_state"],
        "readiness_note": record["readiness_note"],
        "album_fields": record["album_fields"],
        "missing_album_fields": record["missing_album_fields"],
        "summary": record["summary"],
        "tracks": record["tracks"],
        "assessed_at": record["assessed_at"],
        "rules_version": record["rules_version"],
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_readiness": False,
        "current_truth_note": record["current_truth_note"],
    }


def _album_required_results(album: dict) -> tuple[list[dict], list[dict]]:
    fields = []
    missing = []
    for field_id, label in ALBUM_REQUIRED:
        value = album.get(field_id)
        status = STATUS_AVAILABLE if normalize_field(value) or value in {"album", "ep", "single"} else STATUS_MISSING
        item = {"id": field_id, "label": label, "status": status, "blocking": True}
        fields.append(item)
        if status == STATUS_MISSING:
            missing.append(item)
    has_tracks = bool(album.get("tracks"))
    tracks_item = {
        "id": "tracks",
        "label": "At least one track",
        "status": STATUS_AVAILABLE if has_tracks else STATUS_MISSING,
        "blocking": True,
    }
    fields.append(tracks_item)
    if not has_tracks:
        missing.append(tracks_item)
    return fields, missing


def _track_assessment(track: dict, artifact_root: str | Path | None) -> dict:
    job = str(track.get("ingest_job_id") or "")
    position = track.get("position")
    record_ref = track.get("song_release_record_ref") or f"ingest/{job}/song_release_record.json"
    if not track.get("song_present"):
        blocking = [{"id": "song_present", "label": "Existing A2L song", "status": STATUS_MISSING, "blocking": True}]
        return {
            "position": position,
            "ingest_job_id": job,
            "song_title": track.get("song_title"),
            "song_present": False,
            "song_release_record_ref": record_ref,
            "release_readiness": INCOMPLETE,
            "approved_lyrics_status": track.get("approved_lyrics_status") or STATUS_MISSING,
            "blocking_missing_fields": blocking,
            "optional_missing_fields": [],
            "source": "SONG_RELEASE_RECORD",
        }
    record = load_or_create_release_record(job, artifact_root=artifact_root, persist=False)
    blocking = []
    optional = []
    for item in record.get("fields") or []:
        if item.get("status") != STATUS_MISSING:
            continue
        gap = {
            "id": item["id"],
            "label": item.get("label") or FIELD_LABELS.get(item["id"], item["id"]),
            "status": STATUS_MISSING,
            "blocking": item["id"] in REQUIRED_FOR_READY or item.get("required_for_ready") is True,
        }
        if gap["blocking"]:
            blocking.append(gap)
        else:
            optional.append(gap)
    readiness = READY if not blocking else INCOMPLETE
    approved = next((item for item in record.get("fields") or [] if item.get("id") == "approved_lyrics"), None)
    return {
        "position": position,
        "ingest_job_id": job,
        "song_title": track.get("song_title"),
        "song_present": True,
        "song_release_record_ref": record_ref,
        "release_readiness": readiness,
        "approved_lyrics_status": (approved or {}).get("status") or STATUS_MISSING,
        "blocking_missing_fields": blocking,
        "optional_missing_fields": optional,
        "source": "SONG_RELEASE_RECORD",
    }
