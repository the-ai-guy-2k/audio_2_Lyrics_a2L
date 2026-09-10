"""Audio to Lyrics (A2L) — bounded capabilities.

ACI-ATL-001: audio ingestion.
ACI-ATL-002: CONTROL-A machine transcription (non-authoritative draft).
Vocal isolation remains out of scope.
"""

from a2l.errors import IngestionError, TranscriptionError
from a2l.ingest import IngestResult, ingest_wav
from a2l.transcribe import TranscriptionResult, transcribe_from_manifest
from a2l.wav import AudioMetadata

__all__ = [
    "AudioMetadata",
    "IngestResult",
    "IngestionError",
    "TranscriptionError",
    "TranscriptionResult",
    "ingest_wav",
    "transcribe_from_manifest",
]
