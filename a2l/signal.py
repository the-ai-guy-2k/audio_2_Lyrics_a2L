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
ENERGY_BLOCK_FRAMES = 48000


def pcm_energy(wav_path: Path) -> dict:
    try:
        with wave.open(str(wav_path), "rb") as wav_file:
            sample_width = wav_file.getsampwidth()
            channel_count = wav_file.getnchannels()
            frame_count = wav_file.getnframes()
            peak_abs = 0
            sum_squares = 0.0
            sample_count = 0
            energy_known = True
            while True:
                frames = wav_file.readframes(ENERGY_BLOCK_FRAMES)
                if not frames:
                    break
                samples = _samples_from_frames(frames, sample_width)
                if samples is None:
                    energy_known = False
                    sample_count = 0
                    break
                for value in samples:
                    absolute = abs(value)
                    if absolute > peak_abs:
                        peak_abs = absolute
                    sum_squares += value * value
                    sample_count += 1
    except (OSError, wave.Error) as exc:
        raise TranscriptionError("WORKING_AUDIO_UNREADABLE", f"Could not read working WAV: {exc}") from exc

    if not energy_known:
        return {
            "sample_width_bytes": sample_width,
            "channel_count": channel_count,
            "sample_count": 0,
            "peak_full_scale": None,
            "rms_full_scale": None,
            "energy_known": False,
            "no_signal": False,
        }
    if sample_count == 0:
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
    peak = peak_abs / full_scale
    rms = math.sqrt(sum_squares / sample_count) / full_scale
    return {
        "sample_width_bytes": sample_width,
        "channel_count": channel_count,
        "sample_count": sample_count,
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
    if sample_width == 3:
        samples: list[int] = []
        for index in range(0, len(frames) - 2, 3):
            value = frames[index] | (frames[index + 1] << 8) | (frames[index + 2] << 16)
            if value & 0x800000:
                value -= 0x1000000
            samples.append(value)
        return samples
    if sample_width == 4:
        count = len(frames) // 4
        return list(struct.unpack("<" + "i" * count, frames[: count * 4]))
    return None
