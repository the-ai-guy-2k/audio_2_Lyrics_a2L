"""Transcription engines for the CONTROL-A pipeline.

Primary engine (ACI-A2L-007): faster-whisper / Whisper large-v3 using the
validated ACI-A2L-005 configuration. OpenAI whisper-1 remains in the
codebase as historical code and is not the primary path.

Vocal isolation is not used.
"""

from __future__ import annotations

import os
import tempfile
import warnings
import wave
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
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
                "The openai package is not installed. OpenAI whisper-1 is not the primary A2L engine.",
            ) from exc
        return OpenAI()


PRIMARY_TECHNOLOGY = "faster-whisper"
PRIMARY_MODEL = "large-v3"
PRIMARY_MODEL_REPO = "Systran/faster-whisper-large-v3"
DEFAULT_DOWNLOAD_ROOT = Path.home() / ".cache" / "a2l-faster-whisper" / "models"
EXPECTED_MODEL_BIN_BYTES = 3087284237


def primary_decoding_config() -> dict:
    return {
        "language": "en",
        "task": "transcribe",
        "beam_size": 5,
        "best_of": 5,
        "patience": 1,
        "temperature": 0.0,
        "word_timestamps": True,
        "vad_filter": False,
        "condition_on_previous_text": False,
        "without_timestamps": False,
        "initial_prompt": None,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "notes": (
            "language=en is an album/language assumption, not a lyric rewrite. "
            "vad_filter is off because VAD can drop sung vocals on mastered music. "
            "condition_on_previous_text=False reduces repeated-loop hallucination on songs. "
            "temperature=0 for a single deterministic decoding pass."
        ),
    }


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _local_model_path(download_root: Path) -> Path | None:
    candidate = download_root / PRIMARY_MODEL
    model_bin = candidate / "model.bin"
    config = candidate / "config.json"
    if not model_bin.is_file() or not config.is_file():
        return None
    if model_bin.stat().st_size != EXPECTED_MODEL_BIN_BYTES:
        return None
    return candidate


class FasterWhisperEngine:
    """Validated ACI-A2L-005 faster-whisper / large-v3 configuration. CPU / int8."""

    technology = PRIMARY_TECHNOLOGY
    model = PRIMARY_MODEL

    def __init__(self, download_root: Path | None = None, model_factory=None) -> None:
        self._download_root = Path(download_root) if download_root else DEFAULT_DOWNLOAD_ROOT
        self._model_factory = model_factory

    def transcribe(self, wav_path: Path) -> EngineResult:
        if not wav_path.is_file():
            raise TranscriptionError("WORKING_AUDIO_MISSING", f"Working WAV not found: {wav_path}")
        factory = self._model_factory
        if factory is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscriptionError(
                    "ENGINE_UNAVAILABLE",
                    "faster-whisper is not installed. Install the transcribe extra or use .venv-faster-whisper.",
                ) from exc
            factory = WhisperModel

        decode = primary_decoding_config()
        download_root = self._download_root
        download_root.mkdir(parents=True, exist_ok=True)
        local_dir = _local_model_path(download_root)
        model_id = str(local_dir) if local_dir is not None else PRIMARY_MODEL
        cpu_threads = os.cpu_count() or 0
        captured: list[str] = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if local_dir is not None:
                model = factory(
                    str(local_dir),
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=cpu_threads,
                )
            else:
                model = factory(
                    PRIMARY_MODEL,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=cpu_threads,
                    download_root=str(download_root),
                )
            segment_iter, info = model.transcribe(
                str(wav_path),
                language=decode["language"],
                task=decode["task"],
                beam_size=decode["beam_size"],
                best_of=decode["best_of"],
                patience=decode["patience"],
                temperature=decode["temperature"],
                word_timestamps=decode["word_timestamps"],
                vad_filter=decode["vad_filter"],
                condition_on_previous_text=decode["condition_on_previous_text"],
                without_timestamps=decode["without_timestamps"],
                compression_ratio_threshold=decode["compression_ratio_threshold"],
                log_prob_threshold=decode["log_prob_threshold"],
                no_speech_threshold=decode["no_speech_threshold"],
            )
            segments = tuple(_faster_whisper_segment(item) for item in segment_iter)
            for item in caught:
                captured.append(warnings.formatwarning(item.message, item.category, item.filename, item.lineno))

        text = " ".join((item.text or "").strip() for item in segments).strip()
        language = getattr(info, "language", None)
        return EngineResult(
            technology=self.technology,
            model=self.model,
            text=text,
            language=language,
            segments=segments,
            configuration={
                "model_repo": PRIMARY_MODEL_REPO,
                "device": "cpu",
                "compute_type": "int8",
                "cpu_threads": cpu_threads,
                "decoding": decode,
                "vocal_isolation": "not_applied",
                "stored_resampling": "none",
                "download_root": str(download_root),
                "model_loaded_from": model_id,
                "faster_whisper_version": _package_version("faster-whisper"),
                "ctranslate2_version": _package_version("ctranslate2"),
                "primary_engine_aci": "ACI-A2L-007",
                "warnings": captured,
            },
        )


def _faster_whisper_segment(segment) -> EngineSegment:
    return EngineSegment(
        start_seconds=float(getattr(segment, "start", 0) or 0),
        end_seconds=float(getattr(segment, "end", 0) or 0),
        text=str(getattr(segment, "text", "") or ""),
        avg_logprob=_optional_float(getattr(segment, "avg_logprob", None)),
        no_speech_prob=_optional_float(getattr(segment, "no_speech_prob", None)),
        compression_ratio=_optional_float(getattr(segment, "compression_ratio", None)),
    )


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
