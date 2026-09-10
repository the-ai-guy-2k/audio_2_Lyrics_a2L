"""ACI-ATL-002 — CONTROL-A transcription behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.cli import main
from a2l.engines import EngineResult, EngineSegment, OpenAIWhisperEngine, ScriptedEngine
from a2l.errors import TranscriptionError
from a2l.ingest import ingest_wav
from a2l.transcribe import transcribe_from_manifest
from tests.wav_fixtures import write_pcm_wav


def _ingest_silence(tmp_path: Path):
    source = write_pcm_wav(tmp_path / "mastered.wav")
    return ingest_wav(source, tmp_path / "artifacts")


def test_transcribe_consumes_control_a_manifest(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="",
            language=None,
            segments=(),
            configuration={"mode": "test"},
        )
    )
    result = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert result.draft["control_baseline"] == "CONTROL_A"
    assert result.draft["input"]["working_audio"] == "derived_working/transcription_ready.wav"
    assert result.draft["input"]["vocal_isolation"] == "not_applied"
    assert result.draft["authority"] == "NON_AUTHORITATIVE_MACHINE_DRAFT"
    assert result.draft["approval_status"] == "NOT_APPROVED"
    assert result.draft["usable_as_approved_lyrics"] is False
    assert result.draft_path.is_file()


def test_source_and_working_audio_remain_unchanged(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    source_bytes = ingest.source_path.read_bytes()
    working_bytes = ingest.working_path.read_bytes()
    source_mtime = ingest.source_path.stat().st_mtime_ns
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text="invented"))
    transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert ingest.source_path.read_bytes() == source_bytes
    assert ingest.working_path.read_bytes() == working_bytes
    assert ingest.source_path.stat().st_mtime_ns == source_mtime


def test_no_signal_engine_text_is_flagged_not_approved(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="Thank you for watching",
            segments=(
                EngineSegment(start_seconds=0, end_seconds=0.1, text="Thank you for watching", avg_logprob=-0.1),
            ),
            configuration={"mode": "test"},
        )
    )
    result = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert "NO_SIGNAL" in result.draft["flags"]
    assert "ENGINE_TEXT_ON_NO_SIGNAL" in result.draft["flags"]
    assert "DO_NOT_TREAT_AS_LYRICS" in result.draft["flags"]
    assert result.draft["usable_as_approved_lyrics"] is False
    assert result.draft["engine_text"] == "Thank you for watching"


def test_low_confidence_segments_are_flagged(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="maybe",
            segments=(
                EngineSegment(
                    start_seconds=0,
                    end_seconds=0.1,
                    text="maybe",
                    avg_logprob=-1.5,
                    no_speech_prob=0.9,
                    compression_ratio=3.0,
                ),
            ),
            configuration={"mode": "test"},
        )
    )
    result = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    segment = result.draft["segments"][0]
    assert "LOW_CONFIDENCE" in segment["flags"]
    assert "NO_SPEECH_LIKELY" in segment["flags"]
    assert "POSSIBLE_HALLUCINATION" in segment["flags"]


def test_missing_manifest_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError) as exc:
        transcribe_from_manifest(tmp_path / "missing.json")
    assert exc.value.code == "MANIFEST_NOT_FOUND"


def test_rejects_non_control_a_manifest(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    manifest = json.loads(ingest.manifest_path.read_text(encoding="utf-8"))
    manifest["control_baseline"] = "CONTROL_B"
    ingest.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text=""))
    with pytest.raises(TranscriptionError) as exc:
        transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert exc.value.code == "NOT_CONTROL_A"


def test_rejects_vocal_isolation(tmp_path: Path) -> None:
    ingest = _ingest_silence(tmp_path)
    manifest = json.loads(ingest.manifest_path.read_text(encoding="utf-8"))
    manifest["derived_working"]["vocal_isolation"] = "applied"
    ingest.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text=""))
    with pytest.raises(TranscriptionError) as exc:
        transcribe_from_manifest(ingest.manifest_path, engine=engine)
    assert exc.value.code == "VOCAL_ISOLATION_NOT_AUTHORIZED"


def test_cli_transcribe_success(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    ingest = _ingest_silence(tmp_path)
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text=""))

    def fake_transcribe(manifest_path, engine=None):
        return transcribe_from_manifest(manifest_path, engine=engine)

    monkeypatch.setattr("a2l.cli.transcribe_from_manifest", lambda path: fake_transcribe(path, engine=engine))
    code = main(["transcribe", str(ingest.manifest_path)])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["approval_status"] == "NOT_APPROVED"
    assert payload["usable_as_approved_lyrics"] is False


def test_cli_transcribe_missing_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["transcribe", str(tmp_path / "nope.json")])
    captured = capsys.readouterr()
    assert code == 2
    payload = json.loads(captured.err)
    assert payload["error_code"] == "MANIFEST_NOT_FOUND"


def test_openai_engine_maps_verbose_json() -> None:
    class FakeResponse:
        def model_dump(self):
            return {
                "text": "hello",
                "language": "en",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 1.0,
                        "text": "hello",
                        "avg_logprob": -0.2,
                        "no_speech_prob": 0.01,
                        "compression_ratio": 1.1,
                    }
                ],
            }

    class FakeClient:
        class audio:
            class transcriptions:
                @staticmethod
                def create(**kwargs):
                    assert kwargs["model"] == "whisper-1"
                    assert kwargs["temperature"] == 0
                    assert kwargs["response_format"] == "verbose_json"
                    return FakeResponse()

    result = OpenAIWhisperEngine(client=FakeClient()).transcribe(Path(__file__))
    assert result.text == "hello"
    assert result.segments[0].avg_logprob == pytest.approx(-0.2)


def test_no_lyric_approval_or_isolation_api() -> None:
    import a2l

    assert not hasattr(a2l, "isolate_vocals")
    assert not hasattr(a2l, "approve_lyrics")
    assert not hasattr(a2l, "structure_lyrics")


def test_chunked_upload_offsets_timestamps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from a2l.engines import OpenAIWhisperEngine
    from tests.wav_fixtures import write_pcm_wav

    monkeypatch.setattr("a2l.engines.MAX_UPLOAD_BYTES", 12000)
    wav_path = write_pcm_wav(tmp_path / "long.wav", channel_count=1, frame_count=20000)
    calls = {"n": 0}

    class FakeResponse:
        def __init__(self, index: int):
            self._index = index

        def model_dump(self):
            return {
                "text": f"part{self._index}",
                "language": "en",
                "segments": [{"start": 0.0, "end": 0.2, "text": f"part{self._index}"}],
            }

    class FakeClient:
        class audio:
            class transcriptions:
                @staticmethod
                def create(**kwargs):
                    calls["n"] += 1
                    return FakeResponse(calls["n"])

    result = OpenAIWhisperEngine(client=FakeClient()).transcribe(wav_path)
    assert calls["n"] >= 2
    assert result.configuration["chunked_upload"] is True
    assert result.segments[0].start_seconds == pytest.approx(0.0)
    assert result.segments[-1].start_seconds > 0

