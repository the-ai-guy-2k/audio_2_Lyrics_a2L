"""Synthetic WAV fixtures for ACI-ATL-001 tests. Not musical recordings."""

from __future__ import annotations

import io
import struct
import wave
from pathlib import Path


def pcm_wav_bytes(
    *,
    sample_rate: int = 44100,
    channel_count: int = 2,
    sample_width: int = 2,
    frame_count: int = 4410,
) -> bytes:
    frames = b"\x00" * (frame_count * channel_count * sample_width)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channel_count)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def write_pcm_wav(path: Path, **kwargs) -> Path:
    path.write_bytes(pcm_wav_bytes(**kwargs))
    return path


def truncated_wav_bytes() -> bytes:
    data = pcm_wav_bytes(frame_count=100)
    return data[:24]


def riff_but_not_wave_bytes() -> bytes:
    return b"RIFF" + struct.pack("<I", 32) + b"AVI " + (b"\x00" * 32)
