"""Transcription engines for the CONTROL-A baseline.

Engine choice is an ACI-ATL-002 baseline implementation, not a GVCA-locked
architecture. Vocal isolation is not used.

Files larger than the Whisper API upload limit are sent as temporary PCM
WAV slices of the CONTROL-A working file. Chunks are not stored as working
artifacts and are not resampled, mixed down, or isolated.
"""

from __future__ import annotations

import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from a2l.errors import TranscriptionError

# Whisper API payload limit is 25 MB. Stay under it without resampling.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class EngineSegment:
    start_seconds: float
    end_seconds: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None


@dataclass(frozen=True)
class EngineResult:
    technology: str
    model: str
    text: str
    language: str | None = None
    segments: tuple[EngineSegment, ...] = ()
    configuration: dict = field(default_factory=dict)


class TranscriptionEngine(Protocol):
    technology: str
    model: str

    def transcribe(self, wav_path: Path) -> EngineResult:
        """Return raw engine output. Do not polish or invent lyrics."""


class ScriptedEngine:
    """Deterministic engine for tests. Does not call a network or model."""

    def __init__(self, result: EngineResult) -> None:
        self.technology = result.technology
        self.model = result.model
        self._result = result

    def transcribe(self, wav_path: Path) -> EngineResult:
        if not wav_path.is_file():
            raise TranscriptionError("WORKING_AUDIO_MISSING", f"Working WAV not found: {wav_path}")
        return self._result


class OpenAIWhisperEngine:
    """OpenAI Audio Transcriptions API, whisper-1, verbose_json, temperature 0."""

    technology = "openai_whisper_api"
    model = "whisper-1"

    def __init__(self, client=None) -> None:
        self._client = client

    def transcribe(self, wav_path: Path) -> EngineResult:
        if not wav_path.is_file():
            raise TranscriptionError("WORKING_AUDIO_MISSING", f"Working WAV not found: {wav_path}")
        client = self._client or self._build_client()
        size = wav_path.stat().st_size
        if size <= MAX_UPLOAD_BYTES:
            result = self._transcribe_one(client, wav_path)
            result.configuration["chunked_upload"] = False
            result.configuration["chunk_count"] = 1
            result.configuration["chunk_boundary_seconds"] = []
            return result
        return self._transcribe_chunked(client, wav_path)

    def _transcribe_one(self, client, wav_path: Path) -> EngineResult:
        try:
            with wav_path.open("rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="verbose_json",
                    temperature=0,
                )
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError("ENGINE_FAILED", f"Whisper API transcription failed: {exc}") from exc
        payload = _response_to_dict(response)
        segments = tuple(_segment_from_payload(item, offset=0.0) for item in payload.get("segments") or [])
        return EngineResult(
            technology=self.technology,
            model=self.model,
            text=str(payload.get("text") or ""),
            language=payload.get("language"),
            segments=segments,
            configuration={
                "response_format": "verbose_json",
                "temperature": 0,
                "prompt": None,
                "vocal_isolation": "not_applied",
                "stored_resampling": "none",
            },
        )

    def _transcribe_chunked(self, client, wav_path: Path) -> EngineResult:
        texts: list[str] = []
        segments: list[EngineSegment] = []
        language = None
        boundaries: list[float] = []
        with tempfile.TemporaryDirectory(prefix="a2l-whisper-chunks-") as tmp:
            for index, (offset, chunk_path) in enumerate(_pcm_wav_chunks(wav_path, Path(tmp))):
                if index > 0:
                    boundaries.append(offset)
                part = self._transcribe_one(client, chunk_path)
                if language is None:
                    language = part.language
                if part.text.strip():
                    texts.append(part.text.strip())
                segments.extend(
                    EngineSegment(
                        start_seconds=item.start_seconds + offset,
                        end_seconds=item.end_seconds + offset,
                        text=item.text,
                        avg_logprob=item.avg_logprob,
                        no_speech_prob=item.no_speech_prob,
                        compression_ratio=item.compression_ratio,
                    )
                    for item in part.segments
                )
        merged = EngineResult(
            technology=self.technology,
            model=self.model,
            text="\n".join(texts),
            language=language,
            segments=tuple(segments),
            configuration={
                "response_format": "verbose_json",
                "temperature": 0,
                "prompt": None,
                "vocal_isolation": "not_applied",
                "stored_resampling": "none",
                "chunked_upload": True,
                "chunk_count": len(boundaries) + 1,
                "chunk_boundary_seconds": boundaries,
                "chunk_reason": "whisper_api_25mb_limit",
            },
        )
        return merged

    def _build_client(self):
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            raise TranscriptionError(
                "ENGINE_UNAVAILABLE",
                "OPENAI_API_KEY is not set. CONTROL-A transcription engine cannot run.",
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TranscriptionError(
                "ENGINE_UNAVAILABLE",
                "The openai package is not installed. Install the transcribe extra.",
            ) from exc
        return OpenAI()


def _pcm_wav_chunks(wav_path: Path, tmp: Path):
    """Yield (start_seconds, temp_wav_path) slices. Original format is unchanged."""
    with wave.open(str(wav_path), "rb") as source:
        channel_count = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frame_count = source.getnframes()
        bytes_per_frame = channel_count * sample_width
        if bytes_per_frame <= 0:
            raise TranscriptionError("INVALID_WAV", "Working WAV has invalid frame size.")
        max_frames = max(1, (MAX_UPLOAD_BYTES - 4096) // bytes_per_frame)
        start = 0
        index = 0
        while start < frame_count:
            count = min(max_frames, frame_count - start)
            source.setpos(start)
            frames = source.readframes(count)
            chunk_path = tmp / f"chunk_{index:03d}.wav"
            with wave.open(str(chunk_path), "wb") as dest:
                dest.setnchannels(channel_count)
                dest.setsampwidth(sample_width)
                dest.setframerate(sample_rate)
                dest.writeframes(frames)
            yield start / float(sample_rate), chunk_path
            start += count
            index += 1


def _segment_from_payload(segment: dict, offset: float) -> EngineSegment:
    return EngineSegment(
        start_seconds=float(segment.get("start") or 0) + offset,
        end_seconds=float(segment.get("end") or 0) + offset,
        text=str(segment.get("text") or ""),
        avg_logprob=_optional_float(segment.get("avg_logprob")),
        no_speech_prob=_optional_float(segment.get("no_speech_prob")),
        compression_ratio=_optional_float(segment.get("compression_ratio")),
    )


def _response_to_dict(response) -> dict:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    data = {}
    for key in ("text", "language", "segments"):
        if hasattr(response, key):
            value = getattr(response, key)
            if key == "segments" and value is not None:
                data[key] = [_response_to_dict(item) if not isinstance(item, dict) else item for item in value]
            else:
                data[key] = value
    return data


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
