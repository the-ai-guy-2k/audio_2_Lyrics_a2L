"""ACI-A2L-DM-002 governed Song Registry.

Persistent Song identity above ingest/artifact trees. References existing
governed artifacts; does not copy or replace their authority.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from a2l.album_manifest import detect_pipeline_dirname
from a2l.approve import APPROVAL_STATUS, default_approved_json_path, default_approved_txt_path
from a2l.errors import SongRegistryError
from a2l.ingest import MANIFEST_FILENAME, SOURCE_FILENAME, WORKING_FILENAME
from a2l.metadata import load_song_metadata
from a2l.pipeline import (
    APPROVED_DIRNAME,
    LOCKED_SHA256,
    ROOT,
    REVIEW_DIRNAME,
    TRANSCRIPTION_DIRNAME,
)
from a2l.song_intelligence_record import RECORD_FILENAME as SIR_FILENAME

RECORD_TYPE_REGISTRY = "A2L_SONG_REGISTRY"
RECORD_TYPE_SONG = "A2L_SONG"
SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-DM-002"
REGISTRY_DIRNAME = "song_registry"
REGISTRY_FILENAME = "song_registry.json"
RELEASE_FILENAME = "song_release_record.json"
METADATA_FILENAME = "song_metadata.json"

STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"
STATUS_NOT_RUN = "NOT_RUN"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_FAILED = "FAILED"

ROLE_CURRENT = "CURRENT"
ROLE_SUPERSEDED = "SUPERSEDED"

AUTHORITY_INPUT = "AUTHORITATIVE INPUT"
AUTHORITY_MEASURED = "MEASURED"


def default_registry_path(artifact_root: str | Path | None = None) -> Path:
    root = Path(artifact_root) if artifact_root is not None else ROOT / "artifacts"
    return root / REGISTRY_DIRNAME / REGISTRY_FILENAME


def register_song(
    ingest_job_id: str,
    *,
    artifact_root: str | Path | None = None,
    song_id: str | None = None,
    now: str | None = None,
) -> dict:
    """Register a Song for an existing ingest job, or return the existing mapping."""
    root = _artifact_root(artifact_root)
    job = _normalize_job_id(ingest_job_id)
    job_dir = _require_ingest_job(job, root)
    stamp = now or _now()
    store = _load_store(root)

    existing_id = (store.get("by_ingest_job_id") or {}).get(job)
    if existing_id:
        song = _songs(store).get(existing_id)
        if not isinstance(song, dict):
            raise SongRegistryError("REGISTRY_CORRUPT", f"Ingest mapping points to missing song_id: {existing_id}")
        return get_song(existing_id, artifact_root=root)

    if song_id is not None:
        sid = _normalize_song_id(song_id)
        if sid in _songs(store):
            raise SongRegistryError("SONG_ID_EXISTS", f"song_id already registered: {sid}")
        _assert_song_id_not_artifact_identity(sid, job)
    else:
        sid = _new_song_id(forbidden={job, *(_songs(store).keys())})

    song = _build_song_record(
        song_id=sid,
        job=job,
        job_dir=job_dir,
        master_revision=1,
        role=ROLE_CURRENT,
        associated_at=stamp,
        created_at=stamp,
        updated_at=stamp,
    )
    store.setdefault("songs", {})[sid] = song
    store.setdefault("by_ingest_job_id", {})[job] = sid
    store["updated_at"] = stamp
    _save_store(store, root)
    return get_song(sid, artifact_root=root)


def associate_master(
    song_id: str,
    ingest_job_id: str,
    *,
    artifact_root: str | Path | None = None,
    make_current: bool = True,
    now: str | None = None,
) -> dict:
    """Associate another ingest/master with an existing Song (multi-master support)."""
    root = _artifact_root(artifact_root)
    sid = _normalize_song_id(song_id)
    job = _normalize_job_id(ingest_job_id)
    job_dir = _require_ingest_job(job, root)
    stamp = now or _now()
    store = _load_store(root)
    song = _songs(store).get(sid)
    if not isinstance(song, dict):
        raise SongRegistryError("SONG_NOT_FOUND", f"Unknown song_id: {sid}")

    mapped = (store.get("by_ingest_job_id") or {}).get(job)
    if mapped and mapped != sid:
        raise SongRegistryError(
            "INGEST_ALREADY_MAPPED",
            f"Ingest job {job} is already associated with song_id {mapped}.",
        )
    if mapped == sid:
        return get_song(sid, artifact_root=root)

    masters = list((song.get("source") or {}).get("masters") or [])
    next_rev = max([int(item.get("master_revision") or 0) for item in masters] + [0]) + 1
    if make_current:
        for item in masters:
            if item.get("role") == ROLE_CURRENT:
                item["role"] = ROLE_SUPERSEDED
    role = ROLE_CURRENT if make_current else ROLE_SUPERSEDED
    masters.append(
        _master_entry(
            job=job,
            job_dir=job_dir,
            master_revision=next_rev,
            role=role,
            associated_at=stamp,
        )
    )
    song["source"] = {
        "current_master_revision": next_rev if make_current else (song.get("source") or {}).get("current_master_revision"),
        "masters": masters,
    }
    if make_current:
        song["lifecycle_state"] = "MASTER_ASSOCIATED"
    song["updated_at"] = stamp
    store["songs"][sid] = song
    store.setdefault("by_ingest_job_id", {})[job] = sid
    store["updated_at"] = stamp
    _save_store(store, root)
    return get_song(sid, artifact_root=root)


def list_songs(artifact_root: str | Path | None = None) -> list[dict]:
    root = _artifact_root(artifact_root)
    store = _load_store(root)
    rows = []
    for sid in sorted(_songs(store).keys()):
        song = get_song(sid, artifact_root=root)
        identity = song.get("identity") or {}
        source = song.get("source") or {}
        current = _current_master(song)
        lyrics = song.get("lyrics") or {}
        intelligence = song.get("intelligence") or {}
        rows.append(
            {
                "song_id": sid,
                "title": identity.get("title"),
                "artist": identity.get("artist"),
                "current_master_revision": source.get("current_master_revision"),
                "current_source_sha256": (current or {}).get("source_sha256"),
                "current_ingest_job_id": (current or {}).get("ingest_job_id"),
                "approved_lyrics_status": lyrics.get("approval_status") or STATUS_MISSING,
                "approved_lyrics_available": bool(lyrics.get("approved_lyrics_ref")),
                "song_intelligence_status": intelligence.get("sir_status") or STATUS_MISSING,
                "song_intelligence_available": bool(intelligence.get("sir_ref")),
                "lifecycle_state": song.get("lifecycle_state"),
            }
        )
    return rows


def get_song(song_id: str, artifact_root: str | Path | None = None) -> dict:
    root = _artifact_root(artifact_root)
    sid = _normalize_song_id(song_id)
    store = _load_store(root)
    song = _songs(store).get(sid)
    if not isinstance(song, dict):
        raise SongRegistryError("SONG_NOT_FOUND", f"Unknown song_id: {sid}")
    return _resolve_song(song, root)


def find_song_id_for_ingest(ingest_job_id: str, artifact_root: str | Path | None = None) -> str | None:
    root = _artifact_root(artifact_root)
    job = _normalize_job_id(ingest_job_id)
    store = _load_store(root)
    value = (store.get("by_ingest_job_id") or {}).get(job)
    return str(value) if value else None


def load_registry(artifact_root: str | Path | None = None) -> dict:
    return _load_store(_artifact_root(artifact_root))


def _build_song_record(
    *,
    song_id: str,
    job: str,
    job_dir: Path,
    master_revision: int,
    role: str,
    associated_at: str,
    created_at: str,
    updated_at: str,
) -> dict:
    return {
        "record_type": RECORD_TYPE_SONG,
        "schema_version": SCHEMA_VERSION,
        "producer_aci": PRODUCER_ACI,
        "song_id": song_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "identity": {
            "title": _missing_value(AUTHORITY_INPUT),
            "artist": _missing_value(AUTHORITY_INPUT),
            "duration_seconds": _missing_value(AUTHORITY_MEASURED),
        },
        "source": {
            "current_master_revision": master_revision if role == ROLE_CURRENT else None,
            "masters": [
                _master_entry(
                    job=job,
                    job_dir=job_dir,
                    master_revision=master_revision,
                    role=role,
                    associated_at=associated_at,
                )
            ],
        },
        "lyrics": {},
        "intelligence": {},
        "release": {},
        "relationships": {"albums": []},
        "lifecycle_state": "REGISTERED",
        "notes": [
            "Song Registry references governed artifacts; it does not replace their authority.",
            "Filename is never used as song title.",
        ],
    }


def _resolve_song(song: dict, artifact_root: Path) -> dict:
    resolved = json.loads(json.dumps(song))
    current = _current_master(resolved)
    if current is None:
        return resolved
    job = current["ingest_job_id"]
    job_dir = artifact_root / "ingest" / job
    if not job_dir.is_dir():
        raise SongRegistryError("INGEST_MISSING", f"Ingest job directory missing for song: {job}")

    meta = load_song_metadata(job, job_dir=job_dir)
    title = meta.get("song_title")
    artist = meta.get("artist")
    duration = _duration_from_manifest(job_dir)
    resolved["identity"] = {
        "title": _governed_value(title, AUTHORITY_INPUT, f"ingest/{job}/{METADATA_FILENAME}"),
        "artist": _governed_value(artist, AUTHORITY_INPUT, f"ingest/{job}/{METADATA_FILENAME}"),
        "duration_seconds": _governed_value(
            duration,
            AUTHORITY_MEASURED,
            f"ingest/{job}/{MANIFEST_FILENAME}",
        ),
    }

    dirname = detect_pipeline_dirname(job_dir)
    approved_txt = default_approved_txt_path(job, pipeline_dirname=dirname)
    approved_json = default_approved_json_path(job, pipeline_dirname=dirname)
    review_path = job_dir / dirname / REVIEW_DIRNAME / "reviewed_lyric_draft.json"
    draft_path = job_dir / dirname / TRANSCRIPTION_DIRNAME / "transcription_draft.json"
    approval_status = "NOT_APPROVED"
    lyric_revision = None
    lyric_authority = None
    transcription = {"engine": None, "model": None, "generated_at": None}
    approved_ref = None
    if approved_txt.is_file() and approved_json.is_file():
        approved_ref = f"ingest/{job}/{dirname}/{APPROVED_DIRNAME}/approved_lyrics.json"
        try:
            payload = json.loads(approved_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if payload.get("approval_status") == APPROVAL_STATUS and payload.get("usable_as_approved_lyrics") is True:
            approval_status = APPROVAL_STATUS
            lyric_authority = payload.get("authority")
            event = payload.get("approval_event") or {}
            lyric_revision = event.get("revision")
            transcription = {
                "engine": payload.get("transcription_engine"),
                "model": payload.get("transcription_model"),
                "generated_at": event.get("approved_at") or payload.get("approved_at"),
            }
    resolved["lyrics"] = {
        "approved_lyrics_ref": approved_ref,
        "review_ref": f"ingest/{job}/{dirname}/{REVIEW_DIRNAME}/reviewed_lyric_draft.json" if review_path.is_file() else None,
        "transcription_draft_ref": (
            f"ingest/{job}/{dirname}/{TRANSCRIPTION_DIRNAME}/transcription_draft.json" if draft_path.is_file() else None
        ),
        "pipeline_dirname": dirname,
        "approval_status": approval_status,
        "lyric_revision": lyric_revision,
        "authority": lyric_authority,
        "transcription_provenance": transcription,
    }

    sir_path = job_dir / SIR_FILENAME
    sir = None
    if sir_path.is_file():
        try:
            sir = json.loads(sir_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sir = None
    if sir:
        resolved["intelligence"] = {
            "sir_ref": f"ingest/{job}/{SIR_FILENAME}",
            "sir_revision": sir.get("revision"),
            "sir_status": STATUS_AVAILABLE,
            "rhythm_structure": _sir_section_ref(sir, "rhythm_structure"),
            "key_mode": _sir_section_ref(sir, "key_mode"),
            "audio_intelligence": _sir_section_ref(sir, "audio_intelligence"),
            "lyric_intelligence": _sir_section_ref(sir, "lyric_intelligence"),
        }
    else:
        resolved["intelligence"] = {
            "sir_ref": None,
            "sir_revision": None,
            "sir_status": STATUS_MISSING,
            "rhythm_structure": {"section_ref": "sir.rhythm_structure", "run_state": STATUS_NOT_RUN},
            "key_mode": {"section_ref": "sir.key_mode", "run_state": STATUS_NOT_RUN},
            "audio_intelligence": {"section_ref": "sir.audio_intelligence", "run_state": STATUS_NOT_RUN},
            "lyric_intelligence": {"section_ref": "sir.lyric_intelligence", "run_state": STATUS_NOT_RUN},
        }

    release_path = job_dir / RELEASE_FILENAME
    if release_path.is_file():
        readiness = None
        try:
            release = json.loads(release_path.read_text(encoding="utf-8"))
            readiness = release.get("release_readiness")
        except json.JSONDecodeError:
            release = None
        resolved["release"] = {
            "song_release_record_ref": f"ingest/{job}/{RELEASE_FILENAME}",
            "release_readiness": readiness,
        }
    else:
        resolved["release"] = {
            "song_release_record_ref": None,
            "release_readiness": None,
        }

    resolved.setdefault("relationships", {"albums": []})
    if approval_status == APPROVAL_STATUS:
        resolved["lifecycle_state"] = "LYRICS_APPROVED"
    elif sir:
        resolved["lifecycle_state"] = "INTELLIGENCE_PRESENT"
    elif release_path.is_file():
        resolved["lifecycle_state"] = "RELEASE_PRESENT"
    else:
        resolved["lifecycle_state"] = resolved.get("lifecycle_state") or "MASTER_ASSOCIATED"
    return resolved


def _sir_section_ref(sir: dict, section_id: str) -> dict:
    section = sir.get(section_id) or {}
    return {
        "section_ref": f"sir.{section_id}",
        "run_state": section.get("run_state") or STATUS_NOT_RUN,
        "authority": section.get("authority"),
        "result_origin": section.get("result_origin"),
    }


def _master_entry(*, job: str, job_dir: Path, master_revision: int, role: str, associated_at: str) -> dict:
    manifest = _load_manifest(job_dir)
    source = manifest.get("authoritative_source") or {}
    sha = source.get("sha256") or job
    return {
        "master_revision": master_revision,
        "role": role,
        "source_sha256": sha,
        "ingest_job_id": job,
        "source_ref": f"ingest/{job}/authoritative_source/{SOURCE_FILENAME}",
        "working_ref": f"ingest/{job}/derived_working/{WORKING_FILENAME}",
        "ingest_manifest_ref": f"ingest/{job}/{MANIFEST_FILENAME}",
        "associated_at": associated_at,
        "notes": "Master bytes identify an audio asset, not the Song.",
    }


def _current_master(song: dict) -> dict | None:
    masters = (song.get("source") or {}).get("masters") or []
    for item in masters:
        if item.get("role") == ROLE_CURRENT:
            return item
    return masters[-1] if masters else None


def _governed_value(value, authority: str, source_ref: str | None) -> dict:
    if value is None or value == "":
        return _missing_value(authority, source_ref)
    return {
        "value": value,
        "status": STATUS_AVAILABLE,
        "authority": authority,
        "source_ref": source_ref,
    }


def _missing_value(authority: str, source_ref: str | None = None) -> dict:
    return {
        "value": None,
        "status": STATUS_MISSING,
        "authority": authority,
        "source_ref": source_ref,
    }


def _duration_from_manifest(job_dir: Path):
    manifest = _load_manifest(job_dir)
    audio = manifest.get("audio") or {}
    return audio.get("duration_seconds")


def _load_manifest(job_dir: Path) -> dict:
    path = job_dir / MANIFEST_FILENAME
    if not path.is_file():
        raise SongRegistryError("MANIFEST_MISSING", f"ingest_manifest.json missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SongRegistryError("MANIFEST_INVALID", "ingest_manifest.json is not valid JSON.") from exc


def _empty_store(now: str | None = None) -> dict:
    stamp = now or _now()
    return {
        "record_type": RECORD_TYPE_REGISTRY,
        "schema_version": SCHEMA_VERSION,
        "producer_aci": PRODUCER_ACI,
        "created_at": stamp,
        "updated_at": stamp,
        "songs": {},
        "by_ingest_job_id": {},
        "notes": [
            "A2L Song Registry index. Song records reference governed ingest artifacts.",
            "song_id is independent of source SHA / ingest_job_id.",
        ],
    }


def _load_store(artifact_root: Path) -> dict:
    path = default_registry_path(artifact_root)
    if not path.is_file():
        return _empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SongRegistryError("REGISTRY_INVALID", "song_registry.json is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise SongRegistryError("REGISTRY_INVALID", "song_registry.json must be an object.")
    payload.setdefault("songs", {})
    payload.setdefault("by_ingest_job_id", {})
    return payload


def _save_store(store: dict, artifact_root: Path) -> Path:
    path = default_registry_path(artifact_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = dict(store)
    document["record_type"] = RECORD_TYPE_REGISTRY
    document["schema_version"] = SCHEMA_VERSION
    document["producer_aci"] = PRODUCER_ACI
    document.setdefault("created_at", _now())
    document["updated_at"] = store.get("updated_at") or _now()
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix="a2l-song-registry-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    return path.resolve()


def _songs(store: dict) -> dict:
    songs = store.get("songs")
    return songs if isinstance(songs, dict) else {}


def _artifact_root(artifact_root: str | Path | None) -> Path:
    return Path(artifact_root) if artifact_root is not None else ROOT / "artifacts"


def _require_ingest_job(job: str, artifact_root: Path) -> Path:
    job_dir = artifact_root / "ingest" / job
    if not (job_dir / MANIFEST_FILENAME).is_file():
        raise SongRegistryError("INGEST_NOT_FOUND", f"No governed ingest job found: {job}")
    return job_dir


def _normalize_job_id(value: str) -> str:
    job = "".join(ch for ch in str(value or "") if ch.isalnum()).lower()
    if not job:
        raise SongRegistryError("INVALID_INGEST_JOB", "ingest_job_id is required.")
    return job


def _normalize_song_id(value: str) -> str:
    sid = "".join(ch for ch in str(value or "") if ch.isalnum()).lower()
    if len(sid) < 8:
        raise SongRegistryError("INVALID_SONG_ID", "song_id must be an opaque alphanumeric id.")
    return sid


def _new_song_id(forbidden: set[str]) -> str:
    for _ in range(32):
        sid = uuid.uuid4().hex
        if sid not in forbidden and sid != LOCKED_SHA256:
            return sid
    raise SongRegistryError("SONG_ID_FAILED", "Could not allocate a song_id.")


def _assert_song_id_not_artifact_identity(song_id: str, ingest_job_id: str) -> None:
    if song_id == ingest_job_id:
        raise SongRegistryError("INVALID_SONG_ID", "song_id must not equal ingest_job_id / source SHA.")
    if song_id == LOCKED_SHA256:
        raise SongRegistryError("INVALID_SONG_ID", "song_id must not equal the locked source SHA.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
