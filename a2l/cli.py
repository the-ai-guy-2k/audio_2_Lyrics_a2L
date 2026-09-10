"""Command-line entry for A2L audio ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from a2l.errors import IngestionError
from a2l.ingest import ingest_wav


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2l",
        description=(
            "A2L audio ingestion (ACI-ATL-001). "
            "Accepts a WAV file, preserves the original, and writes a CONTROL-A working artifact."
        ),
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return _run_ingest(Path(args.wav_path), Path(args.artifact_root))
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


if __name__ == "__main__":
    raise SystemExit(main())
