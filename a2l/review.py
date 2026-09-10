"""ACI-A2L-006 human review and correction.

Machine text stays traceable. Human corrections are stored separately.
The reviewed draft is not approved lyrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from a2l.errors import ReviewError
from a2l.faster_whisper_draft import assert_not_whisper_baseline, candidate_job_dir
from a2l.pipeline import (
    LOCKED_SHA256,
    REVIEW_DIRNAME,
    STRUCTURE_DIRNAME,
    TRANSCRIPTION_DIRNAME,
    ingest_job_dir,
    pipeline_dir,
)
from a2l.structure import structure_lyrics
from a2l.uncertainty import evaluate_uncertainty

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-006"
REVIEW_FILENAME = "reviewed_lyric_draft.json"
REVIEW_TEXT_FILENAME = "reviewed_lyric_draft.txt"
AUTHORITY = "NON_AUTHORITATIVE_REVIEWED_DRAFT"
SOURCE_MACHINE = "MACHINE"
SOURCE_HUMAN = "HUMAN_CORRECTED"


def default_structured_path(sha: str = LOCKED_SHA256) -> Path:
    return pipeline_dir(ingest_job_dir(sha)) / STRUCTURE_DIRNAME / "structured_lyric_draft.json"


def default_transcription_path(sha: str = LOCKED_SHA256) -> Path:
    return pipeline_dir(ingest_job_dir(sha)) / TRANSCRIPTION_DIRNAME / "transcription_draft.json"


def default_review_dir(sha: str = LOCKED_SHA256) -> Path:
    return pipeline_dir(ingest_job_dir(sha)) / REVIEW_DIRNAME


def default_review_path(sha: str = LOCKED_SHA256) -> Path:
    return default_review_dir(sha) / REVIEW_FILENAME


def ensure_structured_draft(sha: str = LOCKED_SHA256) -> Path:
    structured = default_structured_path(sha)
    if structured.is_file():
        return structured
    transcription = default_transcription_path(sha)
    if transcription.is_file():
        uncertainty = evaluate_uncertainty(transcription)
        return structure_lyrics(uncertainty.report_path).draft_path
    raise ReviewError(
        "STRUCTURED_DRAFT_NOT_FOUND",
        "Primary structured lyric draft not found. Run python -m a2l transcribe, then uncertainty, then structure.",
    )


def load_structured_draft(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ReviewError("STRUCTURED_DRAFT_NOT_FOUND", f"Structured lyric draft not found: {path}")
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewError("STRUCTURED_DRAFT_INVALID", "structured lyric draft is not valid JSON.") from exc
    if draft.get("usable_as_approved_lyrics") is True:
        raise ReviewError("AUTHORITY_VIOLATION", "Structured draft claims approved lyrics.")
    if "lines" not in draft:
        raise ReviewError("STRUCTURED_DRAFT_INVALID", "Structured draft is missing lines.")
    return draft


def review_from_structured(structured: dict, structured_path: Path, sha: str) -> dict:
    lines = []
    for item in structured.get("lines") or []:
        machine_text = item.get("preserved_text")
        if machine_text is None:
            machine_text = item.get("text") or ""
        lines.append(
            {
                "index": item.get("index"),
                "kind": item.get("kind"),
                "start_seconds": item.get("start_seconds"),
                "end_seconds": item.get("end_seconds"),
                "machine_text": machine_text,
                "human_text": machine_text,
                "text_source": SOURCE_MACHINE,
                "corrected": False,
                "corrected_at": None,
                "status": item.get("status"),
                "flags": list(item.get("flags") or []),
                "uncertain": bool(item.get("uncertain")),
                "section_label": item.get("section_label"),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "approval_status": "NOT_APPROVED",
        "usable_as_approved_lyrics": False,
        "lyric_state": "DRAFT",
        "transcription_engine": "faster-whisper",
        "transcription_model": "large-v3",
        "ingest_job_id": sha,
        "structured_draft_path": str(structured_path.resolve()),
        "authority_boundary": {
            "mastered_audio": "AUTHORITATIVE_SOURCE",
            "machine_transcription": "NON_AUTHORITATIVE",
            "structured_lyric_draft": "NON_AUTHORITATIVE",
            "human_corrected_text": "REVIEWED_NOT_APPROVED",
            "human_approved_lyrics": "NOT_PRODUCED",
        },
        "vocal_isolation": "not_applied",
        "llm_rewrite": False,
        "counts": {
            "lines": len(lines),
            "human_corrected": 0,
            "uncertain_lines": sum(1 for line in lines if line.get("uncertain")),
        },
        "lines": lines,
        "notes": [
            "Human review draft. Not approved lyrics.",
            "machine_text is the original machine line and is never overwritten.",
            "human_text holds the operator correction when text_source is HUMAN_CORRECTED.",
        ],
    }


def load_or_create_review(structured_path: str | Path | None = None, sha: str = LOCKED_SHA256) -> dict:
    structured_path = Path(structured_path) if structured_path else ensure_structured_draft(sha)
    structured = load_structured_draft(structured_path)
    review_path = default_review_path(sha)
    if review_path.is_file():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        _assert_machine_traceable(review, structured)
        return review
    review = review_from_structured(structured, structured_path, sha)
    prior = _existing_review_for_merge(sha)
    if prior is not None:
        _merge_matching_corrections(review, prior)
    return review


def _existing_review_for_merge(sha: str) -> dict | None:
    candidate = candidate_job_dir(sha) / "human_review" / REVIEW_FILENAME
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def _merge_matching_corrections(review: dict, prior: dict) -> dict:
    prior_by_index = {int(line["index"]): line for line in prior.get("lines") or []}
    for line in review.get("lines") or []:
        old = prior_by_index.get(int(line["index"]))
        if old is None:
            continue
        if old.get("machine_text") != line.get("machine_text"):
            continue
        if old.get("text_source") != SOURCE_HUMAN:
            continue
        line["human_text"] = old.get("human_text")
        line["text_source"] = SOURCE_HUMAN
        line["corrected"] = True
        line["corrected_at"] = old.get("corrected_at")
    review["counts"]["human_corrected"] = sum(
        1 for line in review["lines"] if line.get("text_source") == SOURCE_HUMAN
    )
    return review


def apply_corrections(review: dict, updates: dict[int, str], now: str | None = None) -> dict:
    if review.get("approval_status") == "APPROVED" or review.get("usable_as_approved_lyrics") is True:
        raise ReviewError(
            "ALREADY_APPROVED",
            "Approved lyrics cannot be changed through Save. Approval already happened.",
        )
    stamp = now or datetime.now(timezone.utc).isoformat()
    by_index = {int(line["index"]): line for line in review.get("lines") or []}
    for index, human_text in updates.items():
        if index not in by_index:
            raise ReviewError("LINE_NOT_FOUND", f"No review line with index {index}.")
        line = by_index[index]
        if line.get("kind") == "time_gap" and str(human_text).strip():
            raise ReviewError(
                "GAP_FILL_NOT_AUTHORIZED",
                "Time-gap rows cannot be filled with invented lyrics.",
            )
        machine = line.get("machine_text") or ""
        line["human_text"] = human_text
        if human_text == machine:
            line["text_source"] = SOURCE_MACHINE
            line["corrected"] = False
            line["corrected_at"] = None
        else:
            line["text_source"] = SOURCE_HUMAN
            line["corrected"] = True
            line["corrected_at"] = stamp
    review["counts"]["human_corrected"] = sum(
        1 for line in review["lines"] if line.get("text_source") == SOURCE_HUMAN
    )
    review["usable_as_approved_lyrics"] = False
    review["approval_status"] = "NOT_APPROVED"
    review["lyric_state"] = "REVIEWED"
    return review


def save_review(review: dict, sha: str = LOCKED_SHA256) -> Path:
    if review.get("approval_status") == "APPROVED" or review.get("usable_as_approved_lyrics") is True:
        raise ReviewError(
            "ALREADY_APPROVED",
            "Refusing to overwrite an APPROVED review through Save. Saving does not approve lyrics.",
        )
    review["usable_as_approved_lyrics"] = False
    review["approval_status"] = "NOT_APPROVED"
    review["lyric_state"] = "REVIEWED"
    review_dir = default_review_dir(sha)
    review_dir.mkdir(parents=True, exist_ok=True)
    json_path = review_dir / REVIEW_FILENAME
    txt_path = review_dir / REVIEW_TEXT_FILENAME
    assert_not_whisper_baseline(json_path, sha)
    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(_human_readable(review), encoding="utf-8")
    return json_path.resolve()


def load_saved_review(path: str | Path | None = None, sha: str = LOCKED_SHA256) -> dict:
    path = Path(path) if path else default_review_path(sha)
    if not path.is_file():
        raise ReviewError("REVIEW_NOT_FOUND", f"Reviewed lyric artifact not found: {path}")
    review = json.loads(path.read_text(encoding="utf-8"))
    return review


def _assert_machine_traceable(review: dict, structured: dict) -> None:
    structured_by_index = {int(item["index"]): item for item in structured.get("lines") or []}
    for line in review.get("lines") or []:
        original = structured_by_index.get(int(line["index"]))
        if original is None:
            continue
        preserved = original.get("preserved_text")
        if preserved is None:
            preserved = original.get("text") or ""
        if line.get("machine_text") != preserved:
            raise ReviewError(
                "MACHINE_TEXT_LOST",
                f"Line {line.get('index')} machine_text no longer matches the structured draft.",
            )


def _format_clock(value) -> str:
    if value is None:
        return "--:--.-"
    seconds = float(value)
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:05.2f}"


def _human_readable(review: dict) -> str:
    lines = [
        (
            "A2L REVIEWED LYRIC DRAFT — APPROVED (authoritative files are approved_lyrics.txt/json)"
            if review.get("approval_status") == "APPROVED"
            else "A2L REVIEWED LYRIC DRAFT — NOT APPROVED LYRICS"
        ),
        f"Authority: {review['authority']}",
        f"Approval: {review['approval_status']}",
        f"Engine: {review.get('transcription_engine')} / {review.get('transcription_model')}",
        f"Human-corrected lines: {review.get('counts', {}).get('human_corrected')}",
        "",
    ]
    for item in review["lines"]:
        clock = f"{_format_clock(item['start_seconds'])}–{_format_clock(item['end_seconds'])}"
        flag_text = ",".join(item.get("flags") or []) or "none"
        marker = "UNCERTAIN" if item.get("uncertain") else "UNVERIFIED"
        source = item.get("text_source") or SOURCE_MACHINE
        lines.append(f"# L{item['index']} {clock}  {marker}  {source}  flags={flag_text}")
        lines.append(f"MACHINE: {item.get('machine_text')}")
        if item.get("kind") == "time_gap":
            lines.append("[TIME_GAP — no lyrics invented]")
        else:
            lines.append(f"HUMAN:   {item.get('human_text')}")
        lines.append("")
    return "\n".join(lines) + "\n"
