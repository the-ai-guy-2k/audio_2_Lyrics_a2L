"""WAV validation and technical metadata extraction.

Uses the Python standard library only. No resampling, normalization,
or vocal isolation is performed.
"""

from __future__ import annotations

import hashlib
import io
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

from a2l.errors import IngestionError

RIFF_HEADER = b"RIFF"
WAVE_MARKER = b"WAVE"
SUPPORTED_COMPTYPES = {"NONE", "not compressed"}


@dataclass(frozen=True)
class AudioMetadata:
    file_format: str
    container: str
    codec: str
    sample_rate_hz: int
    channel_count: int
    sample_width_bytes: int
    frame_count: int
    duration_seconds: float
    byte_size: int

    def to_dict(self) -> dict:
        return {
            "file_format": self.file_format,
            "container": self.container,
            "codec": self.codec,
            "sample_rate_hz": self.sample_rate_hz,
            "channel_count": self.channel_count,
            "sample_width_bytes": self.sample_width_bytes,
            "frame_count": self.frame_count,
            "duration_seconds": self.duration_seconds,
            "byte_size": self.byte_size,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise IngestionError("READ_FAILED", f"Could not read input file: {exc}") from exc


def validate_wav_bytes(data: bytes) -> AudioMetadata:
    """Validate uncompressed PCM WAV bytes and extract technical metadata."""
    if not data:
        raise IngestionError("EMPTY_INPUT", "Input file is empty.")

    if len(data) < 12 or data[0:4] != RIFF_HEADER or data[8:12] != WAVE_MARKER:
        raise IngestionError(
            "UNSUPPORTED_FORMAT",
            "Input is not a RIFF/WAVE (.wav) file. ACI-ATL-001 requires WAV.",
        )

    try:
        with wave.open(io.BytesIO(data), "rb") as wav_file:
            channel_count = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            comptype = (wav_file.getcomptype() or "NONE").strip().upper()
            compname = (wav_file.getcompname() or "").strip().lower()
    except (wave.Error, EOFError, struct.error) as exc:
        raise IngestionError(
            "CORRUPT_WAV",
            "WAV container could not be parsed. File is corrupt or incomplete.",
        ) from exc

    if comptype not in {"NONE"} and compname not in SUPPORTED_COMPTYPES:
        raise IngestionError(
            "UNSUPPORTED_CODEC",
            f"WAV compression {comptype!r} is not supported. Baseline input must be uncompressed PCM WAV.",
        )

    if channel_count < 1:
        raise IngestionError("INVALID_WAV", "WAV has no audio channels.")
    if sample_rate <= 0:
        raise IngestionError("INVALID_WAV", "WAV sample rate must be greater than zero.")
    if sample_width < 1:
        raise IngestionError("INVALID_WAV", "WAV sample width is invalid.")
    if frame_count <= 0:
        raise IngestionError("EMPTY_AUDIO", "WAV contains no audio frames.")

    duration_seconds = frame_count / float(sample_rate)
    codec = "PCM"

    return AudioMetadata(
        file_format="WAV",
        container="RIFF/WAVE",
        codec=codec,
        sample_rate_hz=sample_rate,
        channel_count=channel_count,
        sample_width_bytes=sample_width,
        frame_count=frame_count,
        duration_seconds=duration_seconds,
        byte_size=len(data),
    )
