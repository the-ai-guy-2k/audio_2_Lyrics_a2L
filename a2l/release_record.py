"""ACI-A2L-REL-001 song release record.

Collects release Current Truth for one ingested song. Missing values stay
MISSING. Values are not invented. This is not distribution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from a2l import pipeline
from a2l.approve import (
    APPROVAL_STATUS,
    AUTHORITY as APPROVED_LYRIC_AUTHORITY,
    STATE_APPROVED,
    default_approved_json_path,
    default_approved_txt_path,
)
from a2l.errors import IngestionError, ReleaseError, ReviewError
from a2l.ingest import MANIFEST_FILENAME, SOURCE_FILENAME
from a2l.metadata import apply_song_metadata, load_song_metadata, normalize_field, write_song_metadata
from a2l.review import load_or_create_review, save_review
from a2l.wav import validate_wav_bytes

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-REL-001"
RECORD_FILENAME = "song_release_record.json"
AUTHORITY = "SONG_RELEASE_RECORD"
STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"
READY = "READY"
INCOMPLETE = "INCOMPLETE"
EXPLICIT = "explicit"
CLEAN = "clean"
EXPLICIT_CLEAN_VALUES = (EXPLICIT, CLEAN)

OPERATOR_KEYS = (
    "featured_artists",
    "track_number",
    "disc_number",
    "explicit_clean",
    "songwriters",
    "composers",
    "producers",
    "copyright_year",
    "copyright_owner",
    "publisher",
    "isrc",
)

REQUIRED_FOR_READY = (
    "song_title",
    "primary_artist",
    "track_duration",
    "explicit_clean",
    "songwriters",
    "copyright_year",
    "copyright_owner",
    "approved_lyrics",
)

FIELD_LABELS = {
    "song_title": "Song Title",
    "primary_artist": "Primary Artist",
    "featured_artists": "Featured Artist(s)",
    "track_number": "Track Number",
    "disc_number": "Disc Number",
    "track_duration": "Track Duration",
    "explicit_clean": "Explicit / Clean status",
    "songwriters": "Songwriter(s)",
    "composers": "Composer(s)",
    "producers": "Producer(s)",
    "copyright_year": "Copyright Year",
    "copyright_owner": "Copyright Owner",
    "publisher": "Publisher / Publishing Information",
    "isrc": "ISRC",
    "master_audio": "Master Audio",
    "approved_lyrics": "Approved Lyrics",
}


def default_release_record_path(
    sha: str,
    job_dir: str | Path | None = None,
    artifact_root: str | Path | None = None,
) -> Path:
    return _job_root(sha, job_dir, artifact_root) / RECORD_FILENAME


def load_or_create_release_record(
    sha: str,
    pipeline_dirname: str | None = None,
    job_dir: str | Path | None = None,
    artifact_root: str | Path | None = None,
    now: str | None = None,
    persist: bool = True,
) -> dict:
    path = default_release_record_path(sha, job_dir=job_dir, artifact_root=artifact_root)
    stored = _read_stored(path)
    record = _assemble(sha, stored, pipeline_dirname=pipeline_dirname, job_dir=job_dir, artifact_root=artifact_root, now=now)
    if persist:
        _write(path, record)
    return record


def save_release_record(
    sha: str,
    updates: dict | None = None,
    pipeline_dirname: str | None = None,
    job_dir: str | Path | None = None,
    artifact_root: str | Path | None = None,
    now: str | None = None,
) -> dict:
    path = default_release_record_path(sha, job_dir=job_dir, artifact_root=artifact_root)
    stored = _read_stored(path)
    operator = dict(stored.get("operator") or {})
    incoming = updates or {}
    if "song_title" in incoming or "primary_artist" in incoming or "artist" in incoming:
        _sync_song_metadata(
            sha,
            incoming.get("song_title") if "song_title" in incoming else None,
            incoming.get("primary_artist") if "primary_artist" in incoming else incoming.get("artist"),
            title_present="song_title" in incoming,
            artist_present="primary_artist" in incoming or "artist" in incoming,
            pipeline_dirname=pipeline_dirname,
            job_dir=job_dir,
            artifact_root=artifact_root,
        )
    for key in OPERATOR_KEYS:
        if key not in incoming:
            continue
        operator[key] = _normalize_operator_value(key, incoming.get(key))
    stored["operator"] = operator
    if stored.get("created_at"):
        stored["created_at"] = stored["created_at"]
    record = _assemble(sha, stored, pipeline_dirname=pipeline_dirname, job_dir=job_dir, artifact_root=artifact_root, now=now)
    _write(path, record)
    return record


def public_release_payload(record: dict) -> dict:
    return {
        "ok": True,
        "release_readiness": record["release_readiness"],
        "release_readiness_note": (
            "READY means this A2L song release record has the required fields. "
            "It does not mean the song has been distributed, delivered to a distributor, "
            "copyright registered, publishing registered, or commercially released."
        ),
        "title_artist_editable": record["title_artist_editable"],
        "usable_as_approved_lyrics": False,
        "fields": record["fields"],
        "ingest_job_id": record["ingest_job_id"],
        "updated_at": record["updated_at"],
        "authority": AUTHORITY,
    }


def _job_root(sha: str, job_dir: str | Path | None, artifact_root: str | Path | None) -> Path:
    if job_dir is not None:
        return Path(job_dir)
    if artifact_root is not None:
        return Path(artifact_root) / "ingest" / sha
    return pipeline.ingest_job_dir(sha)


def _read_stored(path: Path) -> dict:
    if not path.is_file():
        return {"operator": {}, "created_at": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseError("RELEASE_RECORD_INVALID", "song_release_record.json is not valid JSON.") from exc
    operator = payload.get("operator") if isinstance(payload.get("operator"), dict) else {}
    return {
        "operator": {key: operator.get(key) for key in OPERATOR_KEYS},
        "created_at": payload.get("created_at"),
    }


def _assemble(
    sha: str,
    stored: dict,
    pipeline_dirname: str | None,
    job_dir: str | Path | None,
    artifact_root: str | Path | None,
    now: str | None,
) -> dict:
    root = _job_root(sha, job_dir, artifact_root)
    operator = stored.get("operator") or {}
    metadata = load_song_metadata(sha, job_dir=root)
    title = metadata.get("song_title")
    artist = metadata.get("artist")
    duration = _duration_from_audio(root)
    master_path = root / "authoritative_source" / SOURCE_FILENAME
    master_available = master_path.is_file()
    lyrics = _approved_lyrics_ref(sha, pipeline_dirname)
    title_artist_editable = lyrics["status"] != STATUS_AVAILABLE
    stamp = now or datetime.now(timezone.utc).isoformat()
    created = stored.get("created_at") or stamp
    fields = [
        _text_field("song_title", title, required=True, editable=title_artist_editable, source="OPERATOR_PROVIDED_SONG_METADATA"),
        _text_field("primary_artist", artist, required=True, editable=title_artist_editable, source="OPERATOR_PROVIDED_SONG_METADATA"),
        _list_field("featured_artists", operator.get("featured_artists"), required=False),
        _number_field("track_number", operator.get("track_number"), required=False),
        _number_field("disc_number", operator.get("disc_number"), required=False),
        _duration_field(duration),
        _explicit_field(operator.get("explicit_clean")),
        _list_field("songwriters", operator.get("songwriters"), required=True),
        _list_field("composers", operator.get("composers"), required=False),
        _list_field("producers", operator.get("producers"), required=False),
        _text_field("copyright_year", operator.get("copyright_year"), required=True, editable=True, source="OPERATOR_ENTERED"),
        _text_field("copyright_owner", operator.get("copyright_owner"), required=True, editable=True, source="OPERATOR_ENTERED"),
        _text_field("publisher", operator.get("publisher"), required=False, editable=True, source="OPERATOR_ENTERED"),
        _text_field("isrc", operator.get("isrc"), required=False, editable=True, source="OPERATOR_ENTERED"),
        _master_field(master_available, master_path if master_available else None),
        _lyrics_field(lyrics),
    ]
    by_id = {item["id"]: item for item in fields}
    missing_required = [FIELD_LABELS[key] for key in REQUIRED_FOR_READY if by_id[key]["status"] != STATUS_AVAILABLE]
    readiness = READY if not missing_required else INCOMPLETE
    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "ingest_job_id": sha,
        "created_at": created,
        "updated_at": stamp,
        "release_readiness": readiness,
        "missing_required_fields": missing_required,
        "title_artist_editable": title_artist_editable,
        "operator": {key: _stored_operator_value(key, operator.get(key)) for key in OPERATOR_KEYS},
        "fields": fields,
        "notes": [
            "Song release Current Truth for this ingested song.",
            "Missing information is flagged. Values are not invented.",
            "The WAV filename is not used as the song title.",
            "ISRC is never generated automatically.",
            "READY is internal A2L record completeness, not commercial release.",
            "Approved lyric words are referenced, not copied into this artifact.",
        ],
    }


def _sync_song_metadata(
    sha: str,
    song_title,
    artist,
    title_present: bool,
    artist_present: bool,
    pipeline_dirname: str | None,
    job_dir: str | Path | None,
    artifact_root: str | Path | None,
) -> None:
    root = _job_root(sha, job_dir, artifact_root)
    current = load_song_metadata(sha, job_dir=root)
    next_title = song_title if title_present else current.get("song_title")
    next_artist = artist if artist_present else current.get("artist")
    lyrics = _approved_lyrics_ref(sha, pipeline_dirname)
    if lyrics["status"] == STATUS_AVAILABLE:
        same_title = normalize_field(next_title) == current.get("song_title")
        same_artist = normalize_field(next_artist) == current.get("artist")
        if not (same_title and same_artist):
            raise ReviewError(
                "ALREADY_APPROVED",
                "Approved song title and artist cannot be changed until the lyrics are reopened.",
            )
        return
    write_song_metadata(sha, next_title, next_artist, job_dir=root)
    try:
        review = load_or_create_review(sha=sha, pipeline_dirname=pipeline_dirname)
        apply_song_metadata(review, next_title, next_artist)
        save_review(review, sha=sha)
    except ReviewError:
        return


def _duration_from_audio(root: Path) -> float | None:
    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        audio = manifest.get("audio") if isinstance(manifest.get("audio"), dict) else {}
        seconds = audio.get("duration_seconds")
        if isinstance(seconds, (int, float)) and seconds > 0:
            return float(seconds)
    source = root / "authoritative_source" / SOURCE_FILENAME
    if source.is_file():
        try:
            meta = validate_wav_bytes(source.read_bytes())
        except IngestionError:
            return None
        if meta.duration_seconds > 0:
            return float(meta.duration_seconds)
    return None


def _approved_lyrics_ref(sha: str, pipeline_dirname: str | None) -> dict:
    candidates = []
    if pipeline_dirname:
        candidates.append(pipeline_dirname)
    if pipeline.PIPELINE_DIRNAME not in candidates:
        candidates.append(pipeline.PIPELINE_DIRNAME)
    if pipeline.PARAKEET_PIPELINE_DIRNAME not in candidates:
        candidates.append(pipeline.PARAKEET_PIPELINE_DIRNAME)
    for dirname in candidates:
        txt = default_approved_txt_path(sha, pipeline_dirname=dirname)
        js = default_approved_json_path(sha, pipeline_dirname=dirname)
        if not txt.is_file() or not js.is_file():
            continue
        try:
            payload = json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("authority") != APPROVED_LYRIC_AUTHORITY:
            continue
        if payload.get("approval_status") != APPROVAL_STATUS or payload.get("usable_as_approved_lyrics") is not True:
            continue
        return {
            "status": STATUS_AVAILABLE,
            "lyric_state": STATE_APPROVED,
            "pipeline_dirname": dirname,
            "txt_relative": f"{dirname}/approved_lyrics/approved_lyrics.txt",
            "json_relative": f"{dirname}/approved_lyrics/approved_lyrics.json",
            "words_copied": False,
        }
    return {
        "status": STATUS_MISSING,
        "lyric_state": None,
        "pipeline_dirname": pipeline_dirname,
        "txt_relative": None,
        "json_relative": None,
        "words_copied": False,
    }


def _status(value) -> str:
    if value is None:
        return STATUS_MISSING
    if value == "" or value == []:
        return STATUS_MISSING
    return STATUS_AVAILABLE


def _text_field(field_id: str, value, required: bool, editable: bool, source: str) -> dict:
    text = normalize_field(value)
    return {
        "id": field_id,
        "label": FIELD_LABELS[field_id],
        "status": _status(text),
        "required_for_ready": required,
        "editable": editable,
        "input": "text" if editable else "readonly",
        "value": text,
        "display": text or "",
        "source": source,
    }


def _list_field(field_id: str, value, required: bool) -> dict:
    items = _as_name_list(value)
    joined = ", ".join(items) if items else ""
    return {
        "id": field_id,
        "label": FIELD_LABELS[field_id],
        "status": _status(items),
        "required_for_ready": required,
        "editable": True,
        "input": "text",
        "value": items,
        "display": joined,
        "source": "OPERATOR_ENTERED",
    }


def _number_field(field_id: str, value, required: bool) -> dict:
    number = _as_positive_int(value)
    return {
        "id": field_id,
        "label": FIELD_LABELS[field_id],
        "status": _status(number),
        "required_for_ready": required,
        "editable": True,
        "input": "text",
        "value": number,
        "display": "" if number is None else str(number),
        "source": "OPERATOR_ENTERED",
    }


def _duration_field(seconds: float | None) -> dict:
    available = seconds is not None
    display = "" if not available else f"{seconds:.3f} seconds"
    return {
        "id": "track_duration",
        "label": FIELD_LABELS["track_duration"],
        "status": STATUS_AVAILABLE if available else STATUS_MISSING,
        "required_for_ready": True,
        "editable": False,
        "input": "readonly",
        "value": seconds,
        "display": display,
        "source": "INGEST_AUDIO_METADATA",
    }


def _explicit_field(value) -> dict:
    status_value = value if value in EXPLICIT_CLEAN_VALUES else None
    display = "" if status_value is None else status_value
    return {
        "id": "explicit_clean",
        "label": FIELD_LABELS["explicit_clean"],
        "status": _status(status_value),
        "required_for_ready": True,
        "editable": True,
        "input": "select",
        "value": status_value,
        "display": display,
        "options": [{"id": EXPLICIT, "label": "Explicit"}, {"id": CLEAN, "label": "Clean"}],
        "source": "OPERATOR_ENTERED",
    }


def _master_field(available: bool, path: Path | None) -> dict:
    return {
        "id": "master_audio",
        "label": FIELD_LABELS["master_audio"],
        "status": STATUS_AVAILABLE if available else STATUS_MISSING,
        "required_for_ready": False,
        "editable": False,
        "input": "readonly",
        "value": "authoritative_source/source.wav" if available else None,
        "display": "Authoritative ingested master" if available else "",
        "source": "AUTHORITATIVE_SOURCE",
    }


def _lyrics_field(ref: dict) -> dict:
    available = ref.get("status") == STATUS_AVAILABLE
    return {
        "id": "approved_lyrics",
        "label": FIELD_LABELS["approved_lyrics"],
        "status": STATUS_AVAILABLE if available else STATUS_MISSING,
        "required_for_ready": True,
        "editable": False,
        "input": "readonly",
        "value": ref.get("txt_relative") if available else None,
        "display": "Authoritative approved lyric artifact" if available else "",
        "source": "AUTHORITATIVE_APPROVED_LYRICS",
        "words_copied": False,
        "lyric_state": ref.get("lyric_state"),
    }


def _normalize_operator_value(key: str, value):
    if key in {"featured_artists", "songwriters", "composers", "producers"}:
        return _as_name_list(value)
    if key in {"track_number", "disc_number"}:
        return _as_positive_int(value)
    if key == "explicit_clean":
        text = normalize_field(value)
        if text is None:
            return None
        lowered = text.lower()
        if lowered not in EXPLICIT_CLEAN_VALUES:
            raise ReleaseError("INVALID_RELEASE_FIELD", "Explicit / Clean must be explicit or clean, or left empty.")
        return lowered
    if key == "copyright_year":
        text = normalize_field(value)
        if text is None:
            return None
        if not (len(text) == 4 and text.isdigit()):
            raise ReleaseError("INVALID_RELEASE_FIELD", "Copyright year must be a four-digit year, or left empty.")
        return text
    if key == "isrc":
        text = normalize_field(value)
        return text.upper() if text else None
    return normalize_field(value)


def _stored_operator_value(key: str, value):
    try:
        return _normalize_operator_value(key, value)
    except ReleaseError:
        return None


def _as_name_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [normalize_field(part) for part in value.replace(";", ",").split(",")]
        return [part for part in parts if part]
    if isinstance(value, list):
        items = [normalize_field(item) for item in value]
        return [item for item in items if item]
    text = normalize_field(value)
    return [text] if text else []


def _as_positive_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ReleaseError("INVALID_RELEASE_FIELD", "Track and disc numbers must be positive whole numbers, or left empty.")
    if isinstance(value, int):
        number = value
    else:
        text = str(value).strip()
        if not text.isdigit():
            raise ReleaseError("INVALID_RELEASE_FIELD", "Track and disc numbers must be positive whole numbers, or left empty.")
        number = int(text)
    if number < 1:
        raise ReleaseError("INVALID_RELEASE_FIELD", "Track and disc numbers must be positive whole numbers, or left empty.")
    return number


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
