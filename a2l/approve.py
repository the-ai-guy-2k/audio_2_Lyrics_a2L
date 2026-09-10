"""ACI-A2L-008 explicit human approval of reviewed lyrics.

Machine output never becomes approved automatically.
Approval requires confirm=True from a deliberate operator action.
Reopen (ACI-A2L-009 Amendment 01) archives prior approval before edits.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from a2l.errors import ApprovalError
from a2l.faster_whisper_draft import assert_not_whisper_baseline
from a2l.pipeline import (
    APPROVED_DIRNAME,
    LOCKED_SHA256,
    ingest_job_dir,
    pipeline_dir,
)
from a2l.review import default_review_path

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-008"
APPROVED_TXT_NAME = "approved_lyrics.txt"
APPROVED_JSON_NAME = "approved_lyrics.json"
HISTORY_DIRNAME = "history"
STATE_DRAFT = "DRAFT"
STATE_REVIEWED = "REVIEWED"
STATE_REQUIRES_REAPPROVAL = "REQUIRES_REAPPROVAL"
STATE_APPROVED = "APPROVED"
AUTHORITY = "AUTHORITATIVE_APPROVED_LYRICS"
REVIEW_RECORD_AUTHORITY = "HUMAN_REVIEW_PROVENANCE"
REVIEW_DRAFT_AUTHORITY = "NON_AUTHORITATIVE_REVIEWED_DRAFT"
ACTIVE_NOT_APPROVED = "NOT_APPROVED"
APPROVAL_STATUS = "APPROVED"


def default_approved_dir(sha: str) -> Path:
    return pipeline_dir(ingest_job_dir(sha)) / APPROVED_DIRNAME


def default_approved_txt_path(sha: str) -> Path:
    return default_approved_dir(sha) / APPROVED_TXT_NAME


def default_approved_json_path(sha: str) -> Path:
    return default_approved_dir(sha) / APPROVED_JSON_NAME


def default_approved_history_dir(sha: str) -> Path:
    return default_approved_dir(sha) / HISTORY_DIRNAME


def latest_approval_history_dir(sha: str) -> Path | None:
    root = default_approved_history_dir(sha)
    if not root.is_dir():
        return None
    dirs = sorted(path for path in root.iterdir() if path.is_dir())
    return dirs[-1] if dirs else None


def apply_review_authority_fields(review: dict, lyric_state: str) -> dict:
    """Keep review provenance distinct from the active approved-lyric authority."""
    review["lyric_state"] = lyric_state
    if lyric_state == STATE_APPROVED:
        review["authority"] = REVIEW_RECORD_AUTHORITY
        review["active_lyric_authority"] = AUTHORITY
        review["approval_status"] = APPROVAL_STATUS
        review["usable_as_approved_lyrics"] = True
    else:
        review["authority"] = REVIEW_DRAFT_AUTHORITY
        review["active_lyric_authority"] = ACTIVE_NOT_APPROVED
        review["usable_as_approved_lyrics"] = False
        review["approval_status"] = "NOT_APPROVED"
    return review


def lyric_display_state(review: dict, sha: str) -> str:
    if (
        review.get("approval_status") == APPROVAL_STATUS
        and review.get("usable_as_approved_lyrics") is True
        and default_approved_json_path(sha).is_file()
        and default_approved_txt_path(sha).is_file()
    ):
        return STATE_APPROVED
    if review.get("lyric_state") == STATE_REQUIRES_REAPPROVAL or review.get("reopened_at"):
        return STATE_REQUIRES_REAPPROVAL
    if default_review_path(sha).is_file():
        return STATE_REVIEWED
    return STATE_DRAFT


def clean_approved_text(review: dict) -> str:
    lines = []
    for item in review.get("lines") or []:
        if item.get("kind") == "time_gap":
            continue
        text = " ".join(str(item.get("human_text") or "").split()).strip()
        if text:
            lines.append(text)
    return "\n".join(lines) + ("\n" if lines else "")


def approve_reviewed_lyrics(
    review: dict,
    sha: str,
    *,
    confirm: bool,
    now: str | None = None,
) -> dict:
    if confirm is not True:
        raise ApprovalError(
            "APPROVAL_NOT_EXPLICIT",
            "Approval requires explicit confirm=true. Saving review does not approve lyrics.",
        )
    if review.get("approval_status") == APPROVAL_STATUS and review.get("usable_as_approved_lyrics") is True:
        raise ApprovalError("ALREADY_APPROVED", "These lyrics are already APPROVED.")

    stamp = now or datetime.now(timezone.utc).isoformat()
    text = clean_approved_text(review)
    if not text.strip():
        raise ApprovalError("EMPTY_LYRICS", "Cannot approve an empty lyric body.")

    txt_path = default_approved_txt_path(sha)
    json_path = default_approved_json_path(sha)
    assert_not_whisper_baseline(txt_path, sha)
    assert_not_whisper_baseline(json_path, sha)
    default_approved_dir(sha).mkdir(parents=True, exist_ok=True)

    history = latest_approval_history_dir(sha)
    prior = list(review.get("approval_history") or [])
    revision = 1 + len(prior)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "approval_status": APPROVAL_STATUS,
        "usable_as_approved_lyrics": True,
        "lyric_state": STATE_APPROVED,
        "ingest_job_id": sha,
        "source_sha256": sha,
        "transcription_engine": review.get("transcription_engine"),
        "transcription_model": review.get("transcription_model"),
        "approval_event": {
            "approved_at": stamp,
            "approved_by": "OPERATOR",
            "method": "EXPLICIT_CONFIRM",
            "automatic": False,
            "revision": revision,
        },
        "approval_history": prior,
        "supersedes": str(history.resolve()) if history else None,
        "approved_lyric_text": text,
        "vocal_isolation": "not_applied",
        "llm_rewrite": False,
        "notes": [
            "Authoritative approved lyrics. Created only after explicit operator confirmation.",
            "Machine transcription and the reviewed draft remain stored separately.",
            "This review JSON is provenance. Authoritative lyric files are approved_lyrics.txt/json.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(text, encoding="utf-8")

    apply_review_authority_fields(review, STATE_APPROVED)
    review["approved_at"] = stamp
    review["approved_by"] = "OPERATOR"
    review["approval_method"] = "EXPLICIT_CONFIRM"
    review["approval_revision"] = revision
    review["approved_txt_path"] = str(txt_path.resolve())
    review["approved_json_path"] = str(json_path.resolve())
    review["reopened_at"] = None
    boundary = dict(review.get("authority_boundary") or {})
    boundary["human_approved_lyrics"] = "APPROVED"
    boundary["review_record"] = REVIEW_RECORD_AUTHORITY
    review["authority_boundary"] = boundary
    notes = list(review.get("notes") or [])
    notes.append("Operator explicitly approved these lyrics (ACI-A2L-008).")
    review["notes"] = notes
    _write_review_record(review, sha)
    return {
        "review": review,
        "txt_path": txt_path.resolve(),
        "json_path": json_path.resolve(),
        "lyric_state": STATE_APPROVED,
    }


def reopen_approved_lyrics(
    review: dict,
    sha: str,
    *,
    confirm: bool,
    now: str | None = None,
) -> dict:
    if confirm is not True:
        raise ApprovalError(
            "REOPEN_NOT_EXPLICIT",
            "Reopening approved lyrics requires explicit confirm=true.",
        )
    display = lyric_display_state(review, sha)
    if display != STATE_APPROVED:
        raise ApprovalError(
            "NOT_APPROVED",
            "Lyrics are not currently APPROVED, so they cannot be reopened.",
        )

    stamp = now or datetime.now(timezone.utc).isoformat()
    txt_path = default_approved_txt_path(sha)
    json_path = default_approved_json_path(sha)
    history_dir = _archive_current_approval(sha, review, stamp)

    event = {
        "approved_at": review.get("approved_at"),
        "approved_by": review.get("approved_by") or "OPERATOR",
        "method": review.get("approval_method") or "EXPLICIT_CONFIRM",
        "automatic": False,
        "revision": review.get("approval_revision") or 1,
        "archived_dir": str(history_dir),
        "superseded_at": stamp,
    }
    history = list(review.get("approval_history") or [])
    history.append(event)
    review["approval_history"] = history
    review["reopened_at"] = stamp
    review["reopened_by"] = "OPERATOR"
    review["reopen_method"] = "EXPLICIT_CONFIRM"
    review["last_archived_approval_dir"] = str(history_dir)
    apply_review_authority_fields(review, STATE_REQUIRES_REAPPROVAL)
    boundary = dict(review.get("authority_boundary") or {})
    boundary["human_approved_lyrics"] = "REQUIRES_REAPPROVAL"
    boundary["review_record"] = REVIEW_DRAFT_AUTHORITY
    review["authority_boundary"] = boundary
    notes = list(review.get("notes") or [])
    notes.append(
        "Operator reopened approved lyrics for correction (ACI-A2L-009 Amendment 01). Prior approval archived."
    )
    review["notes"] = notes
    _write_review_record(review, sha)
    return {
        "review": review,
        "lyric_state": STATE_REQUIRES_REAPPROVAL,
        "archived_dir": history_dir,
        "txt_path": txt_path if txt_path.is_file() else None,
        "json_path": json_path if json_path.is_file() else None,
    }


def _archive_current_approval(sha: str, review: dict, stamp: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ".-" else "-" for ch in stamp)
    history_dir = default_approved_history_dir(sha) / safe
    history_dir.mkdir(parents=True, exist_ok=True)
    txt_path = default_approved_txt_path(sha)
    json_path = default_approved_json_path(sha)
    archived_txt = history_dir / APPROVED_TXT_NAME
    archived_json = history_dir / APPROVED_JSON_NAME
    assert_not_whisper_baseline(history_dir, sha)
    if txt_path.is_file():
        shutil.move(str(txt_path), archived_txt)
    if json_path.is_file():
        shutil.move(str(json_path), archived_json)
    manifest = {
        "superseded_at": stamp,
        "prior_approved_at": review.get("approved_at"),
        "prior_approval_event": {
            "approved_at": review.get("approved_at"),
            "approved_by": review.get("approved_by"),
            "method": review.get("approval_method"),
        },
        "archived_txt": str(archived_txt) if archived_txt.is_file() else None,
        "archived_json": str(archived_json) if archived_json.is_file() else None,
        "reason": "EXPLICIT_REOPEN_FOR_CORRECTION",
    }
    (history_dir / "superseded_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return history_dir.resolve()


def _write_review_record(review: dict, sha: str) -> Path:
    from a2l.review import REVIEW_FILENAME, REVIEW_TEXT_FILENAME, _human_readable, default_review_dir

    review_dir = default_review_dir(sha)
    review_dir.mkdir(parents=True, exist_ok=True)
    json_path = review_dir / REVIEW_FILENAME
    txt_path = review_dir / REVIEW_TEXT_FILENAME
    assert_not_whisper_baseline(json_path, sha)
    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(_human_readable(review), encoding="utf-8")
    return json_path.resolve()


def locked_song_is_unapproved() -> bool:
    sha = LOCKED_SHA256
    if default_approved_txt_path(sha).is_file() or default_approved_json_path(sha).is_file():
        return False
    path = default_review_path(sha)
    if not path.is_file():
        return True
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("approval_status") == APPROVAL_STATUS:
        return False
    if review.get("usable_as_approved_lyrics") is True:
        return False
    return True
