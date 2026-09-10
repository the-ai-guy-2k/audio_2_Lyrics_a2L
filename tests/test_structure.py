"""ACI-ATL-004 — lyric structuring tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2l.cli import main
from a2l.engines import EngineResult, EngineSegment, ScriptedEngine
from a2l.errors import StructureError
from a2l.ingest import ingest_wav
from a2l.structure import structure_lyrics
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import evaluate_uncertainty
from tests.wav_fixtures import write_pcm_wav


def _pipeline(tmp_path: Path, engine: ScriptedEngine, wav_bytes: bytes | None = None):
    source = write_pcm_wav(tmp_path / "mastered.wav")
    if wav_bytes is not None:
        source.write_bytes(wav_bytes)
    ingest = ingest_wav(source, tmp_path / "artifacts")
    transcribed = transcribe_from_manifest(ingest.manifest_path, engine=engine)
    uncertainty = evaluate_uncertainty(transcribed.draft_path)
    return transcribed, uncertainty


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


def test_structure_preserves_text_and_uncertainty(tmp_path: Path) -> None:
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
    transcribed, uncertainty = _pipeline(tmp_path, engine)
    draft_bytes = transcribed.draft_path.read_bytes()
    report_bytes = uncertainty.report_path.read_bytes()
    result = structure_lyrics(uncertainty.report_path)
    machine = [line for line in result.draft["lines"] if line["kind"] == "machine_line"]
    assert machine[0]["preserved_text"] == "maybe these words"
    assert machine[0]["text"] == "maybe these words"
    assert machine[0]["status"] == "REQUIRES_LATER_RESOLUTION"
    assert machine[0]["uncertain"] is True
    assert result.draft["usable_as_approved_lyrics"] is False
    assert result.draft["rewritten_text"] is None
    assert result.draft["section_labels_assigned"] is False
    assert machine[0]["section_label"] is None
    assert transcribed.draft_path.read_bytes() == draft_bytes
    assert uncertainty.report_path.read_bytes() == report_bytes


def test_structure_does_not_invent_verse_chorus(tmp_path: Path) -> None:
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="line one",
            segments=(EngineSegment(start_seconds=0.0, end_seconds=1.0, text="line one"),),
            configuration={"mode": "test"},
        )
    )
    _, uncertainty = _pipeline(tmp_path, engine)
    result = structure_lyrics(uncertainty.report_path)
    assert result.draft["section_labels_assigned"] is False
    assert all(line["section_label"] is None for line in result.draft["lines"])


def test_time_gap_is_flagged_not_filled(tmp_path: Path) -> None:
    engine = ScriptedEngine(
        EngineResult(
            technology="scripted",
            model="test",
            text="first second",
            segments=(
                EngineSegment(
                    start_seconds=0.0,
                    end_seconds=1.0,
                    text="first",
                    avg_logprob=-0.1,
                    no_speech_prob=0.01,
                    compression_ratio=1.1,
                ),
                EngineSegment(
                    start_seconds=5.0,
                    end_seconds=6.0,
                    text="second",
                    avg_logprob=-0.1,
                    no_speech_prob=0.01,
                    compression_ratio=1.1,
                ),
            ),
            configuration={"mode": "test"},
        )
    )
    _, uncertainty = _pipeline(tmp_path, engine, wav_bytes=_non_silent_wav())
    result = structure_lyrics(uncertainty.report_path)
    gaps = [line for line in result.draft["lines"] if line["kind"] == "time_gap"]
    assert len(gaps) == 1
    assert gaps[0]["text"] == ""
    assert "TIME_GAP" in gaps[0]["flags"]
    machine = [line for line in result.draft["lines"] if line["kind"] == "machine_line"]
    assert [line["preserved_text"] for line in machine] == ["first", "second"]


def test_missing_report_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(StructureError) as exc:
        structure_lyrics(tmp_path / "missing.json")
    assert exc.value.code == "REPORT_NOT_FOUND"


def test_cli_structure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    engine = ScriptedEngine(EngineResult(technology="scripted", model="test", text="x"))
    _, uncertainty = _pipeline(tmp_path, engine)
    code = main(["structure", str(uncertainty.report_path)])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["usable_as_approved_lyrics"] is False
    assert payload["section_labels_assigned"] is False
    assert Path(payload["draft_path"]).is_file()
