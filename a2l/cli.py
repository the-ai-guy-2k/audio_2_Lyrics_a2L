"""Command-line entry for A2L ingest and CONTROL-A transcription."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from a2l.errors import IngestionError, TranscriptionError, UncertaintyError
from a2l.ingest import ingest_wav
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import evaluate_uncertainty


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2l",
        description="A2L ingest, CONTROL-A transcription, and uncertainty handling.",
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
        help="Transcribe CONTROL-A working audio from an ACI-ATL-001 ingest manifest.",
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


if __name__ == "__main__":
    raise SystemExit(main())
