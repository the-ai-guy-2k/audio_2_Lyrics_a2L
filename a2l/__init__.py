"""Audio to Lyrics (A2L) — bounded capabilities.

ACI-ATL-001: audio ingestion.
ACI-ATL-002: CONTROL-A machine transcription (non-authoritative draft).
ACI-ATL-003: uncertainty handling (flag, do not invent).
ACI-ATL-004: lyric structuring (structure, do not rewrite).
ACI-A2L-007: faster-whisper / Whisper large-v3 is the primary transcription engine.
ACI-A2L-012: NVIDIA Parakeet TDT 0.6B v2 is an alternate engine, not the primary.
ACI-A2L-006: human review and correction (reviewed draft, not approved).
ACI-A2L-008: explicit human approval writes approved lyric artifacts.
ACI-A2L-010: operator application frontend.
ACI-A2L-013: derived approved-lyric export formatting.
ACI-A2L-014: optional operator-provided song title and artist.
ACI-A2L-016: user-download filenames from operator-supplied title/artist.
ACI-A2L-REL-001: song release record (Current Truth; not distribution).
ACI-A2L-REL-002: album release manifest (organizes song records; membership/order).
ACI-A2L-REL-003: album release readiness (A2L INTERNAL READY/INCOMPLETE; not distribution).
ACI-A2L-REL-004: release package export (derived ZIP from current governed truth; not distribution).
Vocal isolation remains out of scope.
"""

from a2l.errors import IngestionError, StructureError, TranscriptionError, UncertaintyError
from a2l.ingest import IngestResult, ingest_wav
from a2l.structure import StructureResult, structure_lyrics
from a2l.transcribe import TranscriptionResult, transcribe_from_manifest
from a2l.uncertainty import UncertaintyResult, evaluate_uncertainty
from a2l.wav import AudioMetadata

__all__ = [
    "AudioMetadata",
    "IngestResult",
    "IngestionError",
    "StructureError",
    "StructureResult",
    "TranscriptionError",
    "TranscriptionResult",
    "UncertaintyError",
    "UncertaintyResult",
    "evaluate_uncertainty",
    "ingest_wav",
    "structure_lyrics",
    "transcribe_from_manifest",
]
