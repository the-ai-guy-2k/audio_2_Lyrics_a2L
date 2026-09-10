"""ACI-ATL-003 — uncertainty handling tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.cli import main
from a2l.engines import EngineResult, EngineSegment, ScriptedEngine
from a2l.errors import UncertaintyError
from a2l.ingest import ingest_wav
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import evaluate_uncertainty
from tests.wav_fixtures import write_pcm_wav


def _draft(tmp_path: Path, engine: ScriptedEngine):
    source = write_pcm_wav(tmp_path / "mastered.wav")
    ingest = ingest_wav(source, tmp_path / "artifacts")
    return transcribe_from_manifest(ingest.manifest_path, engine=engine)


def test_uncertainty_preserves_machine_text_and_does_not_approve(tmp_path: Path) -> None:
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="maybe these words",
            segments=(
                EngineSegment(start_seconds=0.0, end_seconds=1.0, text="maybe these words", avg_logprob=-1.6),
            ),
            configuration={"mode": "test"},
        )
    )
    transcribed = _draft(tmp_path, engine)
    draft_bytes = transcribed.draft_path.read_bytes()
    result = evaluate_uncertainty(transcribed.draft_path)
    assert result.report["usable_as_approved_lyrics"] is False
    assert result.report["established_lyrics_present"] is False
    assert result.report["established_lyrics"] == []
    assert result.report["rewritten_text"] is None
    assert result.report["llm_interpretation"] is False
    assert result.report["preserved_engine_text"] == "maybe these words"
    assert result.report["job_status"] == "REQUIRES_LATER_RESOLUTION"
    assert result.report["items"][0]["status"] == "REQUIRES_LATER_RESOLUTION"
    assert transcribed.draft_path.read_bytes() == draft_bytes


def test_boilerplate_is_flagged_not_rewritten(tmp_path: Path) -> None:
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="Thank you for watching",
            segments=(EngineSegment(start_seconds=0.0, end_seconds=1.0, text="Thank you for watching"),),
            configuration={"mode": "test"},
        )
    )
    transcribed = _draft(tmp_path, engine)
    result = evaluate_uncertainty(transcribed.draft_path)
    assert "WHISPER_BOILERPLATE" in result.report["flags"]
    assert result.report["preserved_engine_text"] == "Thank you for watching"
    assert result.report["rewritten_text"] is None


def test_unverified_text_is_still_not_established(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "tone.wav", frame_count=44100)
    # Non-silent-ish: still zeros, so NO_SIGNAL will apply. Use a non-zero wav.
    source.write_bytes(_non_silent_wav())
    ingest = ingest_wav(source, tmp_path / "artifacts")
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="clear words",
            segments=(
                EngineSegment(
                    start_seconds=0.0,
                    end_seconds=0.2,
                    text="clear words",
                    avg_logprob=-0.1,
                    no_speech_prob=0.01,
                    compression_ratio=1.1,
                ),
            ),
            configuration={"mode": "test"},
        )
    )
    transcribed = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    result = evaluate_uncertainty(transcribed.draft_path)
    assert result.report["items"][0]["status"] == "UNVERIFIED_MACHINE_TEXT"
    assert result.report["established_lyrics_present"] is False
    assert result.report["resolution_required"] is True


def test_does_not_modify_source_or_working_audio(tmp_path: Path) -> None:
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text="x"))
    transcribed = _draft(tmp_path, engine)
    source_bytes = transcribed.source_path.read_bytes()
    working_bytes = transcribed.working_path.read_bytes()
    evaluate_uncertainty(transcribed.draft_path)
    assert transcribed.source_path.read_bytes() == source_bytes
    assert transcribed.working_path.read_bytes() == working_bytes


def test_missing_draft_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(UncertaintyError) as exc:
        evaluate_uncertainty(tmp_path / "missing.json")
    assert exc.value.code == "DRAFT_NOT_FOUND"


def test_cli_uncertainty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text=""))
    transcribed = _draft(tmp_path, engine)
    code = main(["uncertainty", str(transcribed.draft_path)])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["usable_as_approved_lyrics"] is False
    assert payload["established_lyrics_present"] is False


def _non_silent_wav() -> bytes:
    import io
    import wave

    frames = b"\x00\x10" * 4410
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(frames)
    return buffer.getvalue()
