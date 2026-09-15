"""Typed failures for audio ingestion and transcription."""

from __future__ import annotations


class IngestionError(Exception):
    """Clean failure for invalid, unsupported, or corrupt audio input."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class TranscriptionError(Exception):
    """Clean failure for CONTROL-A transcription."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class UncertaintyError(Exception):
    """Clean failure for uncertainty handling."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class StructureError(Exception):
    """Clean failure for lyric structuring."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ReviewError(Exception):
    """Clean failure for human review and correction."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ApprovalError(Exception):
    """Clean failure for explicit lyric approval."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ExportError(Exception):
    """Clean failure for derived approved-lyric export formatting."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ReleaseError(Exception):
    """Clean failure for song release record or album manifest handling."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class SongIntelligenceError(Exception):
    """Clean failure for Song Intelligence product UI orchestration."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
