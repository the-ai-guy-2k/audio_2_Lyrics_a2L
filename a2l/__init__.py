"""Audio to Lyrics (A2L) — bounded capabilities.

ACI-ATL-001 implements audio ingestion only. Transcription, lyric
generation, and vocal isolation are out of scope.
"""

from a2l.errors import IngestionError
from a2l.ingest import IngestResult, ingest_wav
from a2l.wav import AudioMetadata

__all__ = [
    "AudioMetadata",
    "IngestResult",
    "IngestionError",
    "ingest_wav",
]
