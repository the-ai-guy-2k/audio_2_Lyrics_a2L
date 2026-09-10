"""ACI-A2L-007 — primary faster-whisper large-v3 engine tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from a2l.cli import main
from a2l.engines import (
    PRIMARY_MODEL,
    PRIMARY_MODEL_REPO,
    PRIMARY_TECHNOLOGY,
    EngineResult,
    EngineSegment,
    FasterWhisperEngine,
    OpenAIWhisperEngine,
    ScriptedEngine,
)
from a2l.ingest import ingest_wav
from a2l.pipeline import (
    HISTORICAL_WHISPER1_DIRNAME,
    PIPELINE_DIRNAME,
    TRANSCRIPTION_DIRNAME,
    WHISPER1_JSON_SHA256,
    ingest_job_dir,
    is_historical_whisper1_path,
)
from a2l.transcribe import default_transcription_engine, transcribe_from_manifest
from tests.wav_fixtures import write_pcm_wav


def _ingest_silence(tmp_path: Path):
    source = write_pcm_wav(tmp_path / "mastered.wav")
    return ingest_wav(source, tmp_path / "artifacts")


def test_default_engine_is_faster_whisper_large_v3() -> None:
    engine = default_transcription_engine()
    assert isinstance(engine, FasterWhisperEngine)
    assert not isinstance(engine, OpenAIWhisperEngine)
    assert engine.technology == PRIMARY_TECHNOLOGY
    assert engine.model == PRIMARY_MODEL
    assert PRIMARY_MODEL_REPO == "Systran/faster-whisper-large-v3"


def test_primary_draft_is_not_written_to_whisper1_folder(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(EngineResult(technology="faster-whisper", model="large-v3", text="hello"))
    result = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert PIPELINE_DIRNAME in result.draft_path.parts
    assert result.draft_path.parent.name == TRANSCRIPTION_DIRNAME
    historical = ingest.manifest_path.parent / HISTORICAL_WHISPER1_DIRNAME / "transcription_draft.json"
    assert not historical.exists()
    assert not is_historical_whisper1_path(result.draft_path, ingest.manifest_path.parent)
    assert result.draft["engine"]["technology"] == "faster-whisper"
    assert result.draft["engine"]["model"] == "large-v3"
    assert result.draft["engine"]["architecture_status"] == "ACI-A2L-007_PRIMARY_FASTER_WHISPER_LARGE_V3"


def test_faster_whisper_engine_maps_segments(tmp_path: Path) -> None:
    wav_path = write_pcm_wav(tmp_path / "clip.wav")

    class FakeSegment:
        start = 0.0
        end = 1.2
        text = " hello"
        avg_logprob = -0.2
        no_speech_prob = 0.01
        compression_ratio = 1.1

    class FakeInfo:
        language = "en"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def transcribe(self, *args, **kwargs):
            assert kwargs["language"] == "en"
            assert kwargs["temperature"] == 0.0
            assert kwargs["vad_filter"] is False
            assert kwargs["condition_on_previous_text"] is False
            return iter([FakeSegment()]), FakeInfo()

    result = FasterWhisperEngine(download_root=tmp_path / "models", model_factory=FakeModel).transcribe(wav_path)
    assert result.technology == "faster-whisper"
    assert result.model == "large-v3"
    assert result.text == "hello"
    assert result.segments[0].start_seconds == pytest.approx(0.0)
    assert result.configuration["device"] == "cpu"
    assert result.configuration["compute_type"] == "int8"
    assert result.configuration["primary_engine_aci"] == "ACI-A2L-007"


def test_cli_transcribe_uses_faster_whisper_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(EngineResult(technology="faster-whisper", model="large-v3", text="ok"))
    monkeypatch.setattr(
        "a2l.cli.transcribe_from_manifest",
        lambda path: transcribe_from_manifest(path, engine=engine),
    )
    code = main(["transcribe", str(ingest.manifest_path)])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["engine"]["technology"] == "faster-whisper"
    assert payload["engine"]["model"] == "large-v3"
    assert payload["primary_engine_aci"] == "ACI-A2L-007"


def test_historical_whisper1_runtime_hashes_unchanged() -> None:
    job = ingest_job_dir()
    json_path = job / HISTORICAL_WHISPER1_DIRNAME / "transcription_draft.json"
    txt_path = job / HISTORICAL_WHISPER1_DIRNAME / "transcription_draft.txt"
    if not json_path.is_file():
        pytest.skip("locked-song whisper-1 runtime artifacts not present")
    digest = hashlib.sha256(json_path.read_bytes()).hexdigest()
    assert digest == WHISPER1_JSON_SHA256
    if txt_path.is_file():
        assert hashlib.sha256(txt_path.read_bytes()).hexdigest() == (
            "c05fc1227ad6842bb4efa9cf1c375bd392c5fe5361e5a9ad6d49e22864147886"
        )
