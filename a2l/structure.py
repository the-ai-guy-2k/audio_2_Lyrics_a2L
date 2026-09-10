"""ACI-ATL-004 lyric structuring.

Turn uncertainty-annotated machine spans into a structured lyric draft
for human review. Do not rewrite words, invent lyrics, or approve them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from a2l.errors import StructureError
from a2l.pipeline import STRUCTURE_DIRNAME, TRANSCRIPTION_DIRNAME, find_ingest_job_dir, resolve_audio

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-ATL-004"
DRAFT_DIRNAME = STRUCTURE_DIRNAME
DRAFT_FILENAME = "structured_lyric_draft.json"
DRAFT_TEXT_FILENAME = "structured_lyric_draft.txt"

AUTHORITY = "NON_AUTHORITATIVE_STRUCTURED_DRAFT"
GAP_SECONDS = 2.0


@dataclass(frozen=True)
class StructureResult:
    job_id: str
    draft_path: Path
    text_path: Path
    report_path: Path
    draft: dict


def structure_lyrics(uncertainty_report_path: str | Path) -> StructureResult:
    report_path = Path(uncertainty_report_path)
    report = _load_report(report_path)
    pipeline_root = report_path.parent.parent
    draft_path = pipeline_root / TRANSCRIPTION_DIRNAME / "transcription_draft.json"
    draft = _load_transcription_draft(draft_path)
    _assert_texts_match(draft, report)

    ingest_job = find_ingest_job_dir(report_path) or pipeline_root
    source_path = resolve_audio(ingest_job, draft["input"]["authoritative_source"])
    working_path = resolve_audio(ingest_job, draft["input"]["working_audio"])
    source_before = source_path.read_bytes() if source_path.is_file() else None
    working_before = working_path.read_bytes() if working_path.is_file() else None
    draft_before = draft_path.read_bytes()
    report_before = report_path.read_bytes()

    structured = build_structured_draft(draft, report)
    out_dir = pipeline_root / DRAFT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / DRAFT_FILENAME
    out_txt = out_dir / DRAFT_TEXT_FILENAME
    out_json.write_text(json.dumps(structured, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_txt.write_text(_human_readable(structured), encoding="utf-8")

    if source_before is not None and source_path.read_bytes() != source_before:
        raise StructureError("SOURCE_MUTATED", "Authoritative source changed during lyric structuring.")
    if working_before is not None and working_path.read_bytes() != working_before:
        raise StructureError("WORKING_MUTATED", "CONTROL-A working audio changed during lyric structuring.")
    if draft_path.read_bytes() != draft_before:
        raise StructureError("DRAFT_MUTATED", "Transcription draft was rewritten during lyric structuring.")
    if report_path.read_bytes() != report_before:
        raise StructureError("REPORT_MUTATED", "Uncertainty report was rewritten during lyric structuring.")

    return StructureResult(
        job_id=str(report.get("ingest_job_id") or draft.get("ingest_job_id") or ""),
        draft_path=out_json.resolve(),
        text_path=out_txt.resolve(),
        report_path=report_path.resolve(),
        draft=structured,
    )


def build_structured_draft(transcription_draft: dict, uncertainty_report: dict) -> dict:
    if transcription_draft.get("usable_as_approved_lyrics") is True:
        raise StructureError("AUTHORITY_VIOLATION", "Transcription draft claims approved lyrics.")
    if uncertainty_report.get("usable_as_approved_lyrics") is True:
        raise StructureError("AUTHORITY_VIOLATION", "Uncertainty report claims approved lyrics.")

    lines = []
    previous_end = None
    line_index = 0
    for item in uncertainty_report.get("items") or []:
        start = item.get("start_seconds")
        if (
            previous_end is not None
            and start is not None
            and previous_end is not None
            and float(start) - float(previous_end) >= GAP_SECONDS
        ):
            line_index += 1
            lines.append(
                {
                    "index": line_index,
                    "kind": "time_gap",
                    "start_seconds": previous_end,
                    "end_seconds": start,
                    "text": "",
                    "preserved_text": "",
                    "status": "REQUIRES_LATER_RESOLUTION",
                    "flags": ["TIME_GAP"],
                    "uncertain": True,
                    "section_label": None,
                }
            )
        line_index += 1
        preserved = item.get("preserved_text")
        if preserved is None:
            raise StructureError("REPORT_INVALID", "Uncertainty item is missing preserved_text.")
        flags = list(item.get("flags") or [])
        status = item.get("status") or "UNVERIFIED_MACHINE_TEXT"
        lines.append(
            {
                "index": line_index,
                "kind": "machine_line",
                "start_seconds": start,
                "end_seconds": item.get("end_seconds"),
                "text": preserved,
                "preserved_text": preserved,
                "status": status,
                "flags": flags,
                "uncertain": status == "REQUIRES_LATER_RESOLUTION" or bool(flags),
                "section_label": None,
            }
        )
        if item.get("end_seconds") is not None:
            previous_end = item.get("end_seconds")

    machine_lines = [line for line in lines if line["kind"] == "machine_line"]
    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "approval_status": "NOT_APPROVED",
        "usable_as_approved_lyrics": False,
        "established_lyrics_present": False,
        "control_baseline": uncertainty_report.get("control_baseline") or transcription_draft.get("control_baseline"),
        "ingest_job_id": uncertainty_report.get("ingest_job_id") or transcription_draft.get("ingest_job_id"),
        "authority_boundary": {
            "mastered_audio": "AUTHORITATIVE_SOURCE",
            "machine_transcription": "NON_AUTHORITATIVE",
            "structured_lyric_draft": "NON_AUTHORITATIVE",
            "human_approved_lyrics": "NOT_YET_PRODUCED",
        },
        "preserved_engine_text": uncertainty_report.get("preserved_engine_text"),
        "rewritten_text": None,
        "llm_interpretation": False,
        "vocal_isolation": "not_applied",
        "section_labels_assigned": False,
        "flags": list(uncertainty_report.get("flags") or []),
        "counts": {
            "machine_lines": len(machine_lines),
            "time_gaps": sum(1 for line in lines if line["kind"] == "time_gap"),
            "uncertain_lines": sum(1 for line in lines if line.get("uncertain")),
        },
        "lines": lines,
        "notes": [
            "Structured for human review. Not approved lyrics.",
            "FLAG IT — DO NOT INVENT IT: words are preserved from the uncertainty report.",
            "No verse/chorus labels were assigned; that would guess song form.",
            "Time gaps are flagged, not filled with invented lyrics.",
        ],
    }


def _load_report(path: Path) -> dict:
    if not path.is_file():
        raise StructureError("REPORT_NOT_FOUND", f"Uncertainty report not found: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StructureError("REPORT_INVALID", "uncertainty_report.json is not valid JSON.") from exc
    if report.get("produced_by") != "ACI-ATL-003":
        raise StructureError("REPORT_INVALID", "Lyric structuring consumes an ACI-ATL-003 uncertainty report.")
    if "items" not in report or "preserved_engine_text" not in report:
        raise StructureError("REPORT_INVALID", "Uncertainty report is missing required fields.")
    return report


def _load_transcription_draft(path: Path) -> dict:
    if not path.is_file():
        raise StructureError("DRAFT_NOT_FOUND", f"Transcription draft not found: {path}")
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StructureError("DRAFT_INVALID", "transcription_draft.json is not valid JSON.") from exc
    if draft.get("produced_by") != "ACI-ATL-002":
        raise StructureError("DRAFT_INVALID", "Lyric structuring requires the ACI-ATL-002 transcription draft.")
    return draft


def _assert_texts_match(draft: dict, report: dict) -> None:
    if draft.get("engine_text") != report.get("preserved_engine_text"):
        raise StructureError(
            "TEXT_MISMATCH",
            "Uncertainty preserved_engine_text does not match the transcription draft.",
        )


def _format_clock(value) -> str:
    if value is None:
        return "--:--.-"
    seconds = float(value)
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:05.2f}"


def _human_readable(draft: dict) -> str:
    lines = [
        "A2L STRUCTURED LYRIC DRAFT — NOT APPROVED LYRICS",
        f"Authority: {draft['authority']}",
        f"Approval: {draft['approval_status']}",
        f"Usable as approved lyrics: {draft['usable_as_approved_lyrics']}",
        f"Section labels assigned: {draft['section_labels_assigned']}",
        "",
    ]
    for item in draft["lines"]:
        clock = f"{_format_clock(item['start_seconds'])}–{_format_clock(item['end_seconds'])}"
        flag_text = ",".join(item["flags"]) if item["flags"] else "none"
        if item["kind"] == "time_gap":
            lines.append(f"# GAP {clock}  {item['status']}  flags={flag_text}")
            lines.append("[TIME_GAP — no lyrics invented]")
            lines.append("")
            continue
        marker = "UNCERTAIN" if item["uncertain"] else "UNVERIFIED"
        lines.append(f"# L{item['index']} {clock}  {marker}  {item['status']}  flags={flag_text}")
        lines.append(item["preserved_text"])
        lines.append("")
    return "\n".join(lines) + "\n"
