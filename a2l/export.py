"""ACI-A2L-013 derived export formatting of approved lyrics.

Approved lyric words are immutable. These presentations are not the
authoritative approved artifact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from a2l.approve import (
    APPROVAL_STATUS,
    AUTHORITY,
    STATE_APPROVED,
    default_approved_dir,
    default_approved_json_path,
    default_approved_txt_path,
    lyric_display_state,
)
from a2l.errors import ExportError

PRODUCER_ACI = "ACI-A2L-013"
EXPORT_DIRNAME = "exports"
FORMAT_STANDARD = "standard-lyric-sheet"
FORMAT_PLAIN = "plain-text"
FORMAT_STRUCTURED = "structured-lyrics"
DEFAULT_FORMAT = FORMAT_STANDARD
SUPPORTED_FORMATS = (FORMAT_STANDARD, FORMAT_PLAIN, FORMAT_STRUCTURED)
FORMAT_LABELS = {
    FORMAT_STANDARD: "STANDARD LYRIC SHEET",
    FORMAT_PLAIN: "PLAIN TEXT",
    FORMAT_STRUCTURED: "STRUCTURED LYRICS",
}
DOWNLOAD_NAMES = {
    FORMAT_STANDARD: "lyric-sheet.txt",
    FORMAT_PLAIN: "lyrics.txt",
    FORMAT_STRUCTURED: "structured-lyrics.txt",
}
DERIVED_AUTHORITY = "DERIVED_EXPORT_PRESENTATION"


@dataclass(frozen=True)
class ExportResult:
    format_id: str
    label: str
    text: str
    download_name: str
    source_txt: Path
    source_json: Path
    provenance: dict


def default_exports_dir(sha: str, pipeline_dirname: str | None = None) -> Path:
    return default_approved_dir(sha, pipeline_dirname) / EXPORT_DIRNAME


def format_approved_export(
    sha: str,
    format_id: str | None = None,
    pipeline_dirname: str | None = None,
) -> ExportResult:
    selected = format_id or DEFAULT_FORMAT
    if selected not in SUPPORTED_FORMATS:
        raise ExportError("UNKNOWN_FORMAT", "Choose STANDARD LYRIC SHEET, PLAIN TEXT, or STRUCTURED LYRICS.")
    txt_path, json_path, payload, canonical = _load_approved(sha, pipeline_dirname)
    text = _render(selected, payload, canonical)
    _assert_words_preserved(canonical, text, selected, payload)
    provenance = {
        "schema_version": "1.0.0",
        "produced_by": PRODUCER_ACI,
        "authority": DERIVED_AUTHORITY,
        "usable_as_approved_lyrics": False,
        "approval_status": APPROVAL_STATUS,
        "format": selected,
        "format_label": FORMAT_LABELS[selected],
        "source_approved_txt": str(txt_path.resolve()),
        "source_approved_json": str(json_path.resolve()),
        "ingest_job_id": payload.get("ingest_job_id") or sha,
        "transcription_engine": payload.get("transcription_engine"),
        "transcription_model": payload.get("transcription_model"),
        "pipeline_dirname": payload.get("pipeline_dirname") or pipeline_dirname,
        "llm_rewrite": False,
        "notes": [
            "Derived presentation of authoritative approved lyrics.",
            "This file is not the canonical approved artifact.",
            "Approved lyric words were not rewritten.",
        ],
    }
    return ExportResult(
        format_id=selected,
        label=FORMAT_LABELS[selected],
        text=text,
        download_name=DOWNLOAD_NAMES[selected],
        source_txt=txt_path.resolve(),
        source_json=json_path.resolve(),
        provenance=provenance,
    )


def write_derived_exports(sha: str, pipeline_dirname: str | None = None) -> Path:
    out_dir = default_exports_dir(sha, pipeline_dirname)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for format_id in SUPPORTED_FORMATS:
        result = format_approved_export(sha, format_id, pipeline_dirname=pipeline_dirname)
        path = out_dir / DOWNLOAD_NAMES[format_id]
        path.write_text(result.text, encoding="utf-8", newline="\n")
        written.append(
            {
                "format": result.format_id,
                "path": str(path.resolve()),
                "download_name": result.download_name,
            }
        )
    manifest = {
        "produced_by": PRODUCER_ACI,
        "authority": DERIVED_AUTHORITY,
        "usable_as_approved_lyrics": False,
        "default_format": DEFAULT_FORMAT,
        "source_approved_txt": str(default_approved_txt_path(sha, pipeline_dirname).resolve()),
        "source_approved_json": str(default_approved_json_path(sha, pipeline_dirname).resolve()),
        "exports": written,
    }
    (out_dir / "export_provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out_dir.resolve()


def public_export_payload(result: ExportResult) -> dict:
    return {
        "ok": True,
        "format": result.format_id,
        "format_label": result.label,
        "default_format": DEFAULT_FORMAT,
        "formats": [{"id": key, "label": FORMAT_LABELS[key]} for key in SUPPORTED_FORMATS],
        "text": result.text,
        "download_name": result.download_name,
        "usable_as_approved_lyrics": False,
        "authority": DERIVED_AUTHORITY,
        "provenance": result.provenance,
    }


def _load_approved(sha: str, pipeline_dirname: str | None) -> tuple[Path, Path, dict, str]:
    txt_path = default_approved_txt_path(sha, pipeline_dirname)
    json_path = default_approved_json_path(sha, pipeline_dirname)
    if not txt_path.is_file() or not json_path.is_file():
        raise ExportError("NOT_APPROVED", "Lyrics are not approved yet.")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExportError("APPROVED_JSON_INVALID", "approved_lyrics.json is not valid JSON.") from exc
    if payload.get("authority") != AUTHORITY:
        raise ExportError("NOT_APPROVED", "Export formatting consumes authoritative approved lyrics only.")
    if payload.get("approval_status") != APPROVAL_STATUS or payload.get("usable_as_approved_lyrics") is not True:
        raise ExportError("NOT_APPROVED", "Lyrics are not approved yet.")
    canonical = txt_path.read_text(encoding="utf-8")
    json_text = payload.get("approved_lyric_text")
    if json_text is not None and json_text != canonical:
        raise ExportError(
            "APPROVED_TEXT_MISMATCH",
            "approved_lyrics.txt and approved_lyrics.json lyric text do not match.",
        )
    check = dict(payload)
    if not check.get("pipeline_dirname") and pipeline_dirname:
        check["pipeline_dirname"] = pipeline_dirname
    if lyric_display_state(check, sha) != STATE_APPROVED:
        raise ExportError("NOT_APPROVED", "Lyrics are not currently APPROVED.")
    return txt_path, json_path, payload, canonical


def _render(format_id: str, payload: dict, canonical: str) -> str:
    if format_id == FORMAT_PLAIN:
        return canonical
    if format_id == FORMAT_STANDARD:
        header = _metadata_header(payload)
        return header + canonical if header else canonical
    return _structured_text(payload, canonical)


def _metadata_header(payload: dict) -> str:
    title = _clean_meta(payload.get("song_title") if payload.get("song_title") is not None else payload.get("title"))
    artist = _clean_meta(payload.get("artist"))
    lines = []
    if title:
        lines.append(title)
    if artist:
        lines.append(artist)
    if not lines:
        return ""
    return "\n".join(lines) + "\n\n"


def _clean_meta(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _structured_text(payload: dict, canonical: str) -> str:
    items = []
    for item in payload.get("lyric_lines") or []:
        text = " ".join(str(item.get("text") or "").split()).strip()
        if not text:
            continue
        items.append({"text": text, "section_label": _clean_meta(item.get("section_label")) or None})
    joined = "\n".join(part["text"] for part in items)
    expected = canonical[:-1] if canonical.endswith("\n") else canonical
    if not items or joined != expected:
        return canonical
    if not any(part["section_label"] for part in items):
        return canonical
    blocks: list[str] = []
    current_label = object()
    current_lines: list[str] = []
    for part in items:
        label = part["section_label"]
        if label != current_label and current_lines:
            blocks.append(_section_block(current_label, current_lines))
            current_lines = []
        current_label = label
        current_lines.append(part["text"])
    if current_lines:
        blocks.append(_section_block(current_label, current_lines))
    return "\n".join(blocks) + "\n"


def _section_block(label, lines: list[str]) -> str:
    body = "\n".join(lines)
    if isinstance(label, str) and label:
        return f"{label}\n\n{body}\n"
    return f"{body}\n"


def _assert_words_preserved(canonical: str, formatted: str, format_id: str, payload: dict) -> None:
    expected = [line for line in canonical.splitlines() if line.strip()]
    if format_id == FORMAT_STANDARD:
        header = _metadata_header(payload)
        remainder = formatted[len(header) :] if header and formatted.startswith(header) else formatted
        actual = [line for line in remainder.splitlines() if line.strip()]
    elif format_id == FORMAT_STRUCTURED:
        skip = set()
        for item in payload.get("lyric_lines") or []:
            label = _clean_meta(item.get("section_label"))
            if label:
                skip.add(label)
        actual = [line for line in formatted.splitlines() if line.strip() and line.strip() not in skip]
    else:
        actual = [line for line in formatted.splitlines() if line.strip()]
    if actual != expected:
        raise ExportError("LYRIC_WORDS_CHANGED", "Export formatting would change approved lyric words.")
