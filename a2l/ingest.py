"""Ingest a mastered WAV and produce a CONTROL-A working artifact.

Governing rule: artist-owned/mastered audio is authoritative. The source
artifact is never modified. The working artifact is a byte-identical copy
so later transcription experiments can use untreated mastered audio as
CONTROL A. Vocal isolation is not applied.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from a2l.errors import IngestionError
from a2l.wav import AudioMetadata, read_file_bytes, sha256_bytes, validate_wav_bytes

SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-ATL-001"
CONSUMER_ACI = "ACI-ATL-002"
SOURCE_ROLE = "AUTHORITATIVE_SOURCE"
WORKING_ROLE = "DERIVED_WORKING"
CONTROL_BASELINE = "CONTROL_A"
SOURCE_FILENAME = "source.wav"
WORKING_FILENAME = "transcription_ready.wav"
MANIFEST_FILENAME = "ingest_manifest.json"

# Explicitly untreated. ACI-ATL-001 must not introduce CONTROL B/C assumptions.
PREPROCESSING = "none"
VOCAL_ISOLATION = "not_applied"


@dataclass(frozen=True)
class IngestResult:
    job_id: str
    artifact_dir: Path
    source_path: Path
    working_path: Path
    manifest_path: Path
    metadata: AudioMetadata
    source_sha256: str
    working_sha256: str
    byte_identical: bool

    def to_dict(self) -> dict:
        return build_manifest(
            job_id=self.job_id,
            artifact_dir=self.artifact_dir,
            source_path=self.source_path,
            working_path=self.working_path,
            metadata=self.metadata,
            source_sha256=self.source_sha256,
            working_sha256=self.working_sha256,
            original_filename=self.source_path.name,
        )


def ingest_wav(source_path: str | Path, artifact_root: str | Path) -> IngestResult:
    """Validate a WAV file and store source + derived working artifacts.

    The operator-supplied file is read only. It is never overwritten.
    """
    operator_path = Path(source_path)
    artifact_root = Path(artifact_root)

    if not operator_path.exists():
        raise IngestionError("NOT_FOUND", f"Input path does not exist: {operator_path}")
    if not operator_path.is_file():
        raise IngestionError("NOT_A_FILE", f"Input path is not a file: {operator_path}")

    original_bytes = read_file_bytes(operator_path)
    metadata = validate_wav_bytes(original_bytes)
    source_digest = sha256_bytes(original_bytes)

    job_dir = artifact_root / "ingest" / source_digest
    source_dir = job_dir / "authoritative_source"
    working_dir = job_dir / "derived_working"
    source_dest = source_dir / SOURCE_FILENAME
    working_dest = working_dir / WORKING_FILENAME
    manifest_dest = job_dir / MANIFEST_FILENAME

    source_dir.mkdir(parents=True, exist_ok=True)
    working_dir.mkdir(parents=True, exist_ok=True)

    _write_immutable_source(source_dest, original_bytes, source_digest)
    _write_bytes_if_needed(working_dest, original_bytes)

    working_digest = sha256_bytes(working_dest.read_bytes())
    if working_digest != source_digest:
        raise IngestionError(
            "WORKING_ARTIFACT_MISMATCH",
            "Derived working artifact is not byte-identical to the authoritative source.",
        )

    # Confirm the operator's original file was not mutated by this process.
    if sha256_bytes(read_file_bytes(operator_path)) != source_digest:
        raise IngestionError(
            "SOURCE_MUTATED",
            "Operator source file changed during ingest. This is a defect.",
        )

    manifest = build_manifest(
        job_id=source_digest,
        artifact_dir=job_dir,
        source_path=source_dest,
        working_path=working_dest,
        metadata=metadata,
        source_sha256=source_digest,
        working_sha256=working_digest,
        original_filename=operator_path.name,
    )
    _write_json(manifest_dest, manifest)

    return IngestResult(
        job_id=source_digest,
        artifact_dir=job_dir,
        source_path=source_dest.resolve(),
        working_path=working_dest.resolve(),
        manifest_path=manifest_dest.resolve(),
        metadata=metadata,
        source_sha256=source_digest,
        working_sha256=working_digest,
        byte_identical=True,
    )


def build_manifest(
    *,
    job_id: str,
    artifact_dir: Path,
    source_path: Path,
    working_path: Path,
    metadata: AudioMetadata,
    source_sha256: str,
    working_sha256: str,
    original_filename: str,
) -> dict:
    """Stable contract for ACI-ATL-002. No undocumented fields are required."""
    return {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "intended_consumer": CONSUMER_ACI,
        "job_id": job_id,
        "control_baseline": CONTROL_BASELINE,
        "original_filename": original_filename,
        "authoritative_source": {
            "role": SOURCE_ROLE,
            "relative_path": _posix_relative(artifact_dir, source_path),
            "filename": SOURCE_FILENAME,
            "sha256": source_sha256,
            "immutable": True,
            "notes": "Artist-owned/mastered WAV. Never modify or replace this file.",
        },
        "derived_working": {
            "role": WORKING_ROLE,
            "relative_path": _posix_relative(artifact_dir, working_path),
            "filename": WORKING_FILENAME,
            "sha256": working_sha256,
            "byte_identical_to_source": True,
            "transcription_ready": True,
            "preprocessing": PREPROCESSING,
            "vocal_isolation": VOCAL_ISOLATION,
            "notes": (
                "Byte-identical copy of the authoritative source. Untreated CONTROL A. "
                "ACI-ATL-002 must consume this file and must not assume resampling, "
                "normalization, mono mixdown, or vocal isolation."
            ),
        },
        "audio": metadata.to_dict(),
        "out_of_scope": [
            "speech/music transcription",
            "lyric generation",
            "vocal isolation",
            "normalization",
            "resampling",
        ],
    }


def _posix_relative(root: Path, target: Path) -> str:
    return target.resolve().relative_to(root.resolve()).as_posix()


def _write_immutable_source(path: Path, data: bytes, expected_digest: str) -> None:
    if path.exists():
        existing = sha256_bytes(path.read_bytes())
        if existing != expected_digest:
            raise IngestionError(
                "SOURCE_COLLISION",
                "Existing authoritative source does not match the incoming WAV digest.",
            )
        return
    path.write_bytes(data)


def _write_bytes_if_needed(path: Path, data: bytes) -> None:
    if path.exists() and sha256_bytes(path.read_bytes()) == sha256_bytes(data):
        return
    path.write_bytes(data)


def _write_json(path: Path, payload: dict) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(serialized, encoding="utf-8")
