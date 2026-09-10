"""Lightweight WAV energy checks. Not preprocessing and not a working artifact."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from a2l.errors import TranscriptionError

# Peak/RMS as a fraction of full scale. Near-zero digital audio is treated as
# no recoverable vocal signal. This flags model output; it does not invent lyrics.
NO_SIGNAL_PEAK = 1e-4
NO_SIGNAL_RMS = 1e-4


def pcm_energy(wav_path: Path) -> dict:
    try:
        with wave.open(str(wav_path), "rb") as wav_file:
            sample_width = wav_file.getsampwidth()
            channel_count = wav_file.getnchannels()
            frame_count = wav_file.getnframes()
            frames = wav_file.readframes(frame_count)
    except (OSError, wave.Error) as exc:
        raise TranscriptionError("WORKING_AUDIO_UNREADABLE", f"Could not read working WAV: {exc}") from exc

    samples = _samples_from_frames(frames, sample_width)
    if samples is None:
        return {
            "sample_width_bytes": sample_width,
            "channel_count": channel_count,
            "sample_count": 0,
            "peak_full_scale": None,
            "rms_full_scale": None,
            "energy_known": False,
            "no_signal": False,
        }
    if not samples:
        return {
            "sample_width_bytes": sample_width,
            "channel_count": channel_count,
            "sample_count": 0,
            "peak_full_scale": 0.0,
            "rms_full_scale": 0.0,
            "energy_known": True,
            "no_signal": True,
        }

    full_scale = float(2 ** (8 * sample_width - 1))
    peak = max(abs(value) for value in samples) / full_scale
    mean_square = sum(value * value for value in samples) / len(samples)
    rms = math.sqrt(mean_square) / full_scale
    return {
        "sample_width_bytes": sample_width,
        "channel_count": channel_count,
        "sample_count": len(samples),
        "peak_full_scale": peak,
        "rms_full_scale": rms,
        "energy_known": True,
        "no_signal": peak < NO_SIGNAL_PEAK and rms < NO_SIGNAL_RMS,
    }


def _samples_from_frames(frames: bytes, sample_width: int) -> list[int] | None:
    if sample_width == 1:
        return [byte - 128 for byte in frames]
    if sample_width == 2:
        count = len(frames) // 2
        return list(struct.unpack("<" + "h" * count, frames[: count * 2]))
    if sample_width == 4:
        count = len(frames) // 4
        return list(struct.unpack("<" + "i" * count, frames[: count * 4]))
    return None
