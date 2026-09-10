"""ACI-A2L-008 explicit human approval of reviewed lyrics.

Machine output never becomes approved automatically.
Approval requires confirm=True from a deliberate operator action.
"""

from __future__ import annotations

import json
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
STATE_DRAFT = "DRAFT"
STATE_REVIEWED = "REVIEWED"
STATE_APPROVED = "APPROVED"
AUTHORITY = "AUTHORITATIVE_APPROVED_LYRICS"
APPROVAL_STATUS = "APPROVED"


def default_approved_dir(sha: str) -> Path:
    return pipeline_dir(ingest_job_dir(sha)) / APPROVED_DIRNAME


def default_approved_txt_path(sha: str) -> Path:
    return default_approved_dir(sha) / APPROVED_TXT_NAME


def default_approved_json_path(sha: str) -> Path:
    return default_approved_dir(sha) / APPROVED_JSON_NAME


def lyric_display_state(review: dict, sha: str) -> str:
    if (
        review.get("approval_status") == APPROVAL_STATUS
        and review.get("usable_as_approved_lyrics") is True
        and default_approved_json_path(sha).is_file()
        and default_approved_txt_path(sha).is_file()
    ):
        return STATE_APPROVED
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
        },
        "approved_lyric_text": text,
        "vocal_isolation": "not_applied",
        "llm_rewrite": False,
        "notes": [
            "Authoritative approved lyrics. Created only after explicit operator confirmation.",
            "Machine transcription and the reviewed draft remain stored separately.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(text, encoding="utf-8")

    review["lyric_state"] = STATE_APPROVED
    review["approval_status"] = APPROVAL_STATUS
    review["usable_as_approved_lyrics"] = True
    review["approved_at"] = stamp
    review["approved_by"] = "OPERATOR"
    review["approval_method"] = "EXPLICIT_CONFIRM"
    review["approved_txt_path"] = str(txt_path.resolve())
    review["approved_json_path"] = str(json_path.resolve())
    boundary = dict(review.get("authority_boundary") or {})
    boundary["human_approved_lyrics"] = "APPROVED"
    review["authority_boundary"] = boundary
    notes = list(review.get("notes") or [])
    notes.append("Operator explicitly approved these lyrics (ACI-A2L-008).")
    review["notes"] = notes
    _write_review_after_approval(review, sha)
    return {
        "review": review,
        "txt_path": txt_path.resolve(),
        "json_path": json_path.resolve(),
        "lyric_state": STATE_APPROVED,
    }


def _write_review_after_approval(review: dict, sha: str) -> Path:
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
