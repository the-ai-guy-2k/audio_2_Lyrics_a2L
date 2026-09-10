"""Typed failures for audio ingestion."""

from __future__ import annotations


class IngestionError(Exception):
    """Clean failure for invalid, unsupported, or corrupt audio input."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
