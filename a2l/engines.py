"""Transcription engines for the CONTROL-A baseline.

Engine choice is an ACI-ATL-002 baseline implementation, not a GVCA-locked
architecture. Vocal isolation is not used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from a2l.errors import TranscriptionError


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
    """OpenAI Audio Transcriptions API, whisper-1, verbose_json, temperature 0.

    Selected because this workstation has the OpenAI client and API key, and
    does not have local Whisper/torch/ffmpeg. Not locked as A2L architecture.
    """

    technology = "openai_whisper_api"
    model = "whisper-1"

    def __init__(self, client=None) -> None:
        self._client = client

    def transcribe(self, wav_path: Path) -> EngineResult:
        if not wav_path.is_file():
            raise TranscriptionError("WORKING_AUDIO_MISSING", f"Working WAV not found: {wav_path}")
        client = self._client or self._build_client()
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
        segments = tuple(
            EngineSegment(
                start_seconds=float(segment.get("start") or 0),
                end_seconds=float(segment.get("end") or 0),
                text=str(segment.get("text") or ""),
                avg_logprob=_optional_float(segment.get("avg_logprob")),
                no_speech_prob=_optional_float(segment.get("no_speech_prob")),
                compression_ratio=_optional_float(segment.get("compression_ratio")),
            )
            for segment in payload.get("segments") or []
        )
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
