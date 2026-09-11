"""ACI-A2L-014 operator-provided song title and artist.

These fields are identifying metadata, not lyrics. Missing values are
left empty. The WAV filename is never treated as the song title.
"""

from __future__ import annotations

import json
from pathlib import Path

from a2l import pipeline
from a2l.errors import ReviewError

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-014"
METADATA_FILENAME = "song_metadata.json"
AUTHORITY = "OPERATOR_PROVIDED_SONG_METADATA"


def normalize_field(value) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None


def normalize_song_metadata(song_title=None, artist=None) -> dict:
    return {
        "song_title": normalize_field(song_title),
        "artist": normalize_field(artist),
    }


def default_song_metadata_path(sha: str, job_dir: str | Path | None = None) -> Path:
    root = Path(job_dir) if job_dir is not None else pipeline.ingest_job_dir(sha)
    return root / METADATA_FILENAME


def write_song_metadata(sha: str, song_title=None, artist=None, job_dir: str | Path | None = None) -> Path:
    fields = normalize_song_metadata(song_title, artist)
    path = default_song_metadata_path(sha, job_dir=job_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "ingest_job_id": sha,
        "song_title": fields["song_title"],
        "artist": fields["artist"],
        "source_filename_used_as_title": False,
        "inferred_from_filename": False,
        "notes": [
            "Operator-provided identifying metadata. Independent from machine-generated lyrics.",
            "The WAV filename is not the song title.",
            "Missing title or artist is left empty. Values are not invented.",
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path.resolve()


def load_song_metadata(sha: str, job_dir: str | Path | None = None) -> dict:
    path = default_song_metadata_path(sha, job_dir=job_dir)
    if not path.is_file():
        return {
            "song_title": None,
            "artist": None,
            "source_filename_used_as_title": False,
            "inferred_from_filename": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewError("SONG_METADATA_INVALID", "song_metadata.json is not valid JSON.") from exc
    fields = normalize_song_metadata(payload.get("song_title"), payload.get("artist"))
    return {
        "song_title": fields["song_title"],
        "artist": fields["artist"],
        "source_filename_used_as_title": False,
        "inferred_from_filename": False,
    }


def apply_song_metadata(review: dict, song_title=None, artist=None) -> dict:
    if _review_is_approved(review):
        raise ReviewError(
            "ALREADY_APPROVED",
            "Approved song title and artist cannot be changed until the lyrics are reopened.",
        )
    fields = normalize_song_metadata(song_title, artist)
    review["song_title"] = fields["song_title"]
    review["artist"] = fields["artist"]
    return review


def overlay_working_metadata(review: dict, sha: str, job_dir: str | Path | None = None) -> dict:
    if _review_is_approved(review):
        review.setdefault("song_title", None)
        review.setdefault("artist", None)
        return review
    if not default_song_metadata_path(sha, job_dir=job_dir).is_file():
        review.setdefault("song_title", None)
        review.setdefault("artist", None)
        return review
    stored = load_song_metadata(sha, job_dir=job_dir)
    review["song_title"] = stored.get("song_title")
    review["artist"] = stored.get("artist")
    return review


def persist_review_metadata(review: dict, sha: str, job_dir: str | Path | None = None) -> Path:
    return write_song_metadata(sha, review.get("song_title"), review.get("artist"), job_dir=job_dir)


def approved_metadata_fields(review: dict) -> dict:
    fields = normalize_song_metadata(review.get("song_title"), review.get("artist"))
    return {
        "song_title": fields["song_title"],
        "artist": fields["artist"],
    }


def _review_is_approved(review: dict) -> bool:
    return review.get("approval_status") == "APPROVED" or review.get("usable_as_approved_lyrics") is True
