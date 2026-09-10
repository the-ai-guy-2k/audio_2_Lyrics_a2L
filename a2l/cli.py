"""Command-line entry for A2L ingest and CONTROL-A transcription."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from a2l.errors import IngestionError, TranscriptionError, UncertaintyError, StructureError, ReviewError
from a2l.ingest import ingest_wav
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import evaluate_uncertainty
from a2l.structure import structure_lyrics
from a2l.approve import (
    default_approved_json_path,
    default_approved_txt_path,
    latest_approval_history_dir,
    lyric_display_state,
)
from a2l.review import LOCKED_SHA256, default_review_path, load_or_create_review
from a2l.review_server import DEFAULT_HOST, DEFAULT_PORT, serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2l",
        description="A2L ingest, transcription, uncertainty, structuring, human review, and explicit approval.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Validate a WAV file and prepare source + working artifacts.",
    )
    ingest_parser.add_argument("wav_path", help="Path to the authoritative source WAV file.")
    ingest_parser.add_argument(
        "--artifact-root",
        default="artifacts",
        help="Directory that will hold ingest jobs (default: ./artifacts).",
    )

    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe CONTROL-A working audio with faster-whisper / Whisper large-v3.",
    )
    transcribe_parser.add_argument(
        "manifest_path",
        help="Path to ingest_manifest.json produced by ACI-ATL-001.",
    )

    uncertainty_parser = subparsers.add_parser(
        "uncertainty",
        help="Flag uncertainty in an ACI-ATL-002 transcription draft. Does not rewrite lyrics.",
    )
    uncertainty_parser.add_argument(
        "draft_path",
        help="Path to transcription_draft.json produced by ACI-ATL-002.",
    )

    structure_parser = subparsers.add_parser(
        "structure",
        help="Structure an uncertainty report into a lyric draft for human review. Does not rewrite lyrics.",
    )
    structure_parser.add_argument(
        "report_path",
        help="Path to uncertainty_report.json produced by ACI-ATL-003.",
    )

    review_parser = subparsers.add_parser(
        "review",
        help="Open the human review interface. Save does not approve. Approval is a separate explicit action.",
    )
    review_parser.add_argument("--host", default=DEFAULT_HOST)
    review_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    review_parser.add_argument("--no-browser", action="store_true")
    review_parser.add_argument(
        "--job-id",
        default=LOCKED_SHA256,
        help="Ingest job id / source SHA-256 (locked song by default).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return _run_ingest(Path(args.wav_path), Path(args.artifact_root))
    if args.command == "transcribe":
        return _run_transcribe(Path(args.manifest_path))
    if args.command == "uncertainty":
        return _run_uncertainty(Path(args.draft_path))
    if args.command == "structure":
        return _run_structure(Path(args.report_path))
    if args.command == "review":
        return _run_review(args.host, args.port, args.job_id, not args.no_browser)
    parser.error(f"Unknown command: {args.command}")
    return 1


def _run_ingest(wav_path: Path, artifact_root: Path) -> int:
    try:
        result = ingest_wav(wav_path, artifact_root)
    except IngestionError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": exc.message}, indent=2), file=sys.stderr)
        return 2
    payload = {
        "ok": True,
        "job_id": result.job_id,
        "manifest_path": str(result.manifest_path),
        "authoritative_source": str(result.source_path),
        "derived_working": str(result.working_path),
        "source_sha256": result.source_sha256,
        "working_sha256": result.working_sha256,
        "byte_identical": result.byte_identical,
        "audio": result.metadata.to_dict(),
        "control_baseline": "CONTROL_A",
        "produced_by": "ACI-ATL-001",
        "intended_consumer": "ACI-ATL-002",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _run_transcribe(manifest_path: Path) -> int:
    try:
        result = transcribe_from_manifest(manifest_path)
    except TranscriptionError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": exc.message}, indent=2), file=sys.stderr)
        return 2
    payload = {
        "ok": True,
        "job_id": result.job_id,
        "draft_path": str(result.draft_path),
        "text_path": str(result.text_path),
        "authority": result.draft["authority"],
        "approval_status": result.draft["approval_status"],
        "usable_as_approved_lyrics": result.draft["usable_as_approved_lyrics"],
        "flags": result.draft["flags"],
        "engine": result.draft["engine"],
        "produced_by": "ACI-ATL-002",
        "primary_engine_aci": "ACI-A2L-007",
        "control_baseline": result.draft["control_baseline"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _run_uncertainty(draft_path: Path) -> int:
    try:
        result = evaluate_uncertainty(draft_path)
    except UncertaintyError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": exc.message}, indent=2), file=sys.stderr)
        return 2
    payload = {
        "ok": True,
        "job_id": result.job_id,
        "report_path": str(result.report_path),
        "text_path": str(result.text_path),
        "job_status": result.report["job_status"],
        "resolution_required": result.report["resolution_required"],
        "usable_as_approved_lyrics": result.report["usable_as_approved_lyrics"],
        "established_lyrics_present": result.report["established_lyrics_present"],
        "flags": result.report["flags"],
        "counts": result.report["counts"],
        "produced_by": "ACI-ATL-003",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _run_structure(report_path: Path) -> int:
    try:
        result = structure_lyrics(report_path)
    except StructureError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": exc.message}, indent=2), file=sys.stderr)
        return 2
    payload = {
        "ok": True,
        "job_id": result.job_id,
        "draft_path": str(result.draft_path),
        "text_path": str(result.text_path),
        "authority": result.draft["authority"],
        "approval_status": result.draft["approval_status"],
        "usable_as_approved_lyrics": result.draft["usable_as_approved_lyrics"],
        "section_labels_assigned": result.draft["section_labels_assigned"],
        "counts": result.draft["counts"],
        "produced_by": "ACI-ATL-004",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _run_review(host: str, port: int, job_id: str, open_browser: bool) -> int:
    try:
        review = load_or_create_review(sha=job_id)
    except ReviewError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": exc.message}, indent=2), file=sys.stderr)
        return 2
    print("HOW THE OPERATOR OPENS THE HUMAN REVIEW INTERFACE")
    print(f"http://{host}:{port}/")
    print("REVIEWED LYRIC ARTIFACT LOCATION")
    print(str(default_review_path(job_id)))
    print("LYRIC STATE")
    print(lyric_display_state(review, job_id))
    txt = default_approved_txt_path(job_id)
    js = default_approved_json_path(job_id)
    print("APPROVED LYRIC TXT LOCATION")
    print(str(txt.resolve()) if txt.is_file() else "NOT CREATED")
    print("APPROVED LYRIC JSON LOCATION")
    print(str(js.resolve()) if js.is_file() else "NOT CREATED")
    history = latest_approval_history_dir(job_id)
    print("PRIOR APPROVAL ARCHIVE")
    print(str(history.resolve()) if history else "NONE")
    serve(host=host, port=port, sha=job_id, open_browser=open_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
