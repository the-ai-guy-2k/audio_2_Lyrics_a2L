"""ACI-ATL-003 uncertainty handling.

FLAG IT — DO NOT INVENT IT.
Preserve machine transcription. Do not rewrite, guess, or approve lyrics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from a2l.errors import UncertaintyError
from a2l.pipeline import UNCERTAINTY_DIRNAME, find_ingest_job_dir, resolve_audio

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-ATL-003"
REPORT_DIRNAME = UNCERTAINTY_DIRNAME
REPORT_FILENAME = "uncertainty_report.json"
REPORT_TEXT_FILENAME = "uncertainty_report.txt"

AUTHORITY_AUDIO = "AUTHORITATIVE_SOURCE"
AUTHORITY_TRANSCRIPTION = "NON_AUTHORITATIVE_DRAFT"
AUTHORITY_UNCERTAINTY = "REQUIRES_LATER_RESOLUTION"

STATUS_QUESTIONABLE = "REQUIRES_LATER_RESOLUTION"
STATUS_UNVERIFIED = "UNVERIFIED_MACHINE_TEXT"
STATUS_ESTABLISHED = "ESTABLISHED_LYRICS"

QUESTIONABLE_FLAGS = {
    "NO_SIGNAL",
    "ENGINE_TEXT_ON_NO_SIGNAL",
    "DO_NOT_TREAT_AS_LYRICS",
    "LOW_CONFIDENCE",
    "LOW_CONFIDENCE_SEGMENTS",
    "NO_SPEECH_LIKELY",
    "POSSIBLE_HALLUCINATION",
    "EMPTY_SEGMENT",
    "WHISPER_BOILERPLATE",
    "REPEATED_SEGMENT",
    "CHUNK_BOUNDARY",
}

BOILERPLATE_PHRASES = (
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
)

CHUNK_BOUNDARY_WINDOW = 0.35


@dataclass(frozen=True)
class UncertaintyResult:
    job_id: str
    report_path: Path
    text_path: Path
    draft_path: Path
    report: dict


def evaluate_uncertainty(draft_path: str | Path) -> UncertaintyResult:
    draft_path = Path(draft_path)
    draft = _load_draft(draft_path)
    pipeline_root = draft_path.parent.parent
    ingest_job = find_ingest_job_dir(draft_path) or pipeline_root
    source_path = resolve_audio(ingest_job, draft["input"]["authoritative_source"])
    working_path = resolve_audio(ingest_job, draft["input"]["working_audio"])
    source_before = source_path.read_bytes() if source_path.is_file() else None
    working_before = working_path.read_bytes() if working_path.is_file() else None
    draft_before = draft_path.read_bytes()

    report = build_uncertainty_report(draft)
    report_dir = pipeline_root / REPORT_DIRNAME
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / REPORT_FILENAME
    text_path = report_dir / REPORT_TEXT_FILENAME
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(_human_readable(report), encoding="utf-8")

    if source_before is not None and source_path.read_bytes() != source_before:
        raise UncertaintyError("SOURCE_MUTATED", "Authoritative source changed during uncertainty handling.")
    if working_before is not None and working_path.read_bytes() != working_before:
        raise UncertaintyError("WORKING_MUTATED", "CONTROL-A working audio changed during uncertainty handling.")
    if draft_path.read_bytes() != draft_before:
        raise UncertaintyError("DRAFT_MUTATED", "Transcription draft was rewritten during uncertainty handling.")

    return UncertaintyResult(
        job_id=str(draft.get("ingest_job_id") or ""),
        report_path=report_path.resolve(),
        text_path=text_path.resolve(),
        draft_path=draft_path.resolve(),
        report=report,
    )


def build_uncertainty_report(draft: dict) -> dict:
    if draft.get("usable_as_approved_lyrics") is True:
        raise UncertaintyError(
            "AUTHORITY_VIOLATION",
            "Transcription draft claims approved lyrics. Uncertainty handling will not promote it.",
        )

    engine_text = draft.get("engine_text")
    if engine_text is None:
        raise UncertaintyError("DRAFT_INVALID", "Transcription draft is missing engine_text.")
    preserved_text = engine_text

    job_flags = list(draft.get("flags") or [])
    boundaries = list((draft.get("engine") or {}).get("configuration", {}).get("chunk_boundary_seconds") or [])
    items = []
    previous_text = None
    for segment in draft.get("segments") or []:
        flags = list(segment.get("flags") or [])
        text = str(segment.get("text") or "")
        stripped = text.strip().lower()
        if _is_boilerplate(stripped):
            flags.append("WHISPER_BOILERPLATE")
        if previous_text is not None and stripped and stripped == previous_text and len(stripped) >= 20:
            flags.append("REPEATED_SEGMENT")
        start = float(segment.get("start_seconds") or 0)
        if any(abs(start - boundary) <= CHUNK_BOUNDARY_WINDOW for boundary in boundaries):
            flags.append("CHUNK_BOUNDARY")
        flags = sorted(set(flags))
        questionable = bool(set(flags) & QUESTIONABLE_FLAGS)
        items.append(
            {
                "start_seconds": segment.get("start_seconds"),
                "end_seconds": segment.get("end_seconds"),
                "preserved_text": text,
                "flags": flags,
                "status": STATUS_QUESTIONABLE if questionable else STATUS_UNVERIFIED,
                "established_lyrics": False,
            }
        )
        previous_text = stripped

    if _is_boilerplate(str(preserved_text).strip().lower()):
        job_flags.append("WHISPER_BOILERPLATE")
    if any("WHISPER_BOILERPLATE" in item["flags"] for item in items):
        job_flags.append("WHISPER_BOILERPLATE")
    if any("REPEATED_SEGMENT" in item["flags"] for item in items):
        job_flags.append("REPEATED_SEGMENT")
    if any("CHUNK_BOUNDARY" in item["flags"] for item in items):
        job_flags.append("CHUNK_BOUNDARY")

    job_flags = sorted(set(job_flags))
    questionable_count = sum(1 for item in items if item["status"] == STATUS_QUESTIONABLE)
    unverified_count = sum(1 for item in items if item["status"] == STATUS_UNVERIFIED)
    if not items and str(preserved_text).strip():
        questionable = bool(set(job_flags) & QUESTIONABLE_FLAGS) or _is_boilerplate(str(preserved_text).strip().lower())
        items.append(
            {
                "start_seconds": None,
                "end_seconds": None,
                "preserved_text": preserved_text,
                "flags": job_flags,
                "status": STATUS_QUESTIONABLE if questionable else STATUS_UNVERIFIED,
                "established_lyrics": False,
            }
        )
        if questionable:
            questionable_count = 1
        else:
            unverified_count = 1

    resolution_required = True
    if questionable_count or set(job_flags) & QUESTIONABLE_FLAGS:
        job_status = STATUS_QUESTIONABLE
    else:
        job_status = STATUS_UNVERIFIED

    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "ingest_job_id": draft.get("ingest_job_id"),
        "control_baseline": draft.get("control_baseline"),
        "authority_boundary": {
            "mastered_audio": AUTHORITY_AUDIO,
            "machine_transcription": AUTHORITY_TRANSCRIPTION,
            "uncertainty_flag": AUTHORITY_UNCERTAINTY,
        },
        "usable_as_approved_lyrics": False,
        "established_lyrics_present": False,
        "established_lyrics": [],
        "resolution_required": resolution_required,
        "job_status": job_status,
        "flags": job_flags,
        "preserved_engine_text": preserved_text,
        "rewritten_text": None,
        "llm_interpretation": False,
        "vocal_isolation": "not_applied",
        "counts": {
            "segments": len(items),
            "questionable": questionable_count,
            "unverified_machine_text": unverified_count,
            "established": 0,
        },
        "items": items,
        "notes": [
            "FLAG IT — DO NOT INVENT IT.",
            "Uncertain machine text is preserved and flagged. It is not rewritten.",
            "Unverified machine text is still not approved lyrics.",
            "No established/human-approved lyrics exist in this ACI.",
        ],
    }


def _load_draft(path: Path) -> dict:
    if not path.is_file():
        raise UncertaintyError("DRAFT_NOT_FOUND", f"Transcription draft not found: {path}")
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UncertaintyError("DRAFT_INVALID", "transcription_draft.json is not valid JSON.") from exc
    if draft.get("produced_by") != "ACI-ATL-002":
        raise UncertaintyError("DRAFT_INVALID", "Uncertainty handling consumes an ACI-ATL-002 transcription draft.")
    if "engine_text" not in draft or "input" not in draft:
        raise UncertaintyError("DRAFT_INVALID", "Transcription draft is missing required fields.")
    return draft


def _is_boilerplate(text: str) -> bool:
    if not text:
        return False
    return any(phrase in text for phrase in BOILERPLATE_PHRASES)


def _human_readable(report: dict) -> str:
    return (
        "A2L UNCERTAINTY REPORT — NOT APPROVED LYRICS\n"
        f"Job status: {report['job_status']}\n"
        f"Resolution required: {report['resolution_required']}\n"
        f"Established lyrics present: {report['established_lyrics_present']}\n"
        f"Flags: {', '.join(report['flags'])}\n"
        f"Questionable segments: {report['counts']['questionable']}\n"
        f"Unverified machine segments: {report['counts']['unverified_machine_text']}\n"
        f"Established: {report['counts']['established']}\n"
        "\n"
        "--- preserved engine text (not rewritten) ---\n"
        f"{report['preserved_engine_text']}\n"
    )
