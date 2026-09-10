"""ACI-ATL-001 — audio ingestion behavior tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from a2l.cli import main
from a2l.errors import IngestionError
from a2l.ingest import ingest_wav
from tests.wav_fixtures import pcm_wav_bytes, riff_but_not_wave_bytes, truncated_wav_bytes, write_pcm_wav


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_wav_is_ingested(tmp_path: Path) -> None:
    source = write_pcm_wav(
        tmp_path / "mastered.wav",
        sample_rate=48000,
        channel_count=2,
        frame_count=4800,
    )
    result = ingest_wav(source, tmp_path / "artifacts")

    assert result.source_path.is_file()
    assert result.working_path.is_file()
    assert result.manifest_path.is_file()
    assert result.metadata.file_format == "WAV"
    assert result.metadata.sample_rate_hz == 48000
    assert result.metadata.channel_count == 2
    assert result.metadata.duration_seconds == pytest.approx(0.1)
    assert result.byte_identical is True


def test_operator_source_file_remains_unchanged(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    before_bytes = source.read_bytes()
    before_mtime = source.stat().st_mtime_ns
    ingest_wav(source, tmp_path / "artifacts")
    assert source.read_bytes() == before_bytes
    assert source.stat().st_mtime_ns == before_mtime


def test_source_and_working_are_distinguishable(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    result = ingest_wav(source, tmp_path / "artifacts")

    assert "authoritative_source" in str(result.source_path)
    assert "derived_working" in str(result.working_path)
    assert result.source_path != result.working_path
    assert result.source_path.name == "source.wav"
    assert result.working_path.name == "transcription_ready.wav"


def test_working_artifact_is_byte_identical_control_a(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    result = ingest_wav(source, tmp_path / "artifacts")
    assert result.source_sha256 == result.working_sha256
    assert result.source_path.read_bytes() == result.working_path.read_bytes()
    assert result.source_path.read_bytes() == source.read_bytes()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["control_baseline"] == "CONTROL_A"
    assert manifest["derived_working"]["preprocessing"] == "none"
    assert manifest["derived_working"]["vocal_isolation"] == "not_applied"
    assert manifest["derived_working"]["byte_identical_to_source"] is True
    assert manifest["intended_consumer"] == "ACI-ATL-002"


def test_repeat_ingest_is_deterministic(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav", sample_rate=44100, channel_count=1)
    first = ingest_wav(source, tmp_path / "artifacts")
    first_manifest = result_bytes = first.manifest_path.read_bytes()
    second = ingest_wav(source, tmp_path / "artifacts")

    assert first.job_id == second.job_id
    assert first.source_sha256 == second.source_sha256
    assert first.working_sha256 == second.working_sha256
    assert first.working_path.read_bytes() == second.working_path.read_bytes()
    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes() == first_manifest
    assert result_bytes == second.manifest_path.read_bytes()


def test_invalid_non_audio_fails_cleanly(tmp_path: Path) -> None:
    bogus = tmp_path / "notes.txt"
    bogus.write_text("this is not audio", encoding="utf-8")
    with pytest.raises(IngestionError) as exc:
        ingest_wav(bogus, tmp_path / "artifacts")
    assert exc.value.code == "UNSUPPORTED_FORMAT"
    assert not (tmp_path / "artifacts" / "ingest").exists()


def test_wav_extension_with_text_fails_cleanly(tmp_path: Path) -> None:
    fake = tmp_path / "song.wav"
    fake.write_text("not a wav", encoding="utf-8")
    with pytest.raises(IngestionError) as exc:
        ingest_wav(fake, tmp_path / "artifacts")
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_corrupt_wav_fails_cleanly(tmp_path: Path) -> None:
    corrupt = tmp_path / "broken.wav"
    corrupt.write_bytes(truncated_wav_bytes())
    with pytest.raises(IngestionError) as exc:
        ingest_wav(corrupt, tmp_path / "artifacts")
    assert exc.value.code == "CORRUPT_WAV"


def test_riff_non_wave_fails_cleanly(tmp_path: Path) -> None:
    fake = tmp_path / "clip.wav"
    fake.write_bytes(riff_but_not_wave_bytes())
    with pytest.raises(IngestionError) as exc:
        ingest_wav(fake, tmp_path / "artifacts")
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_missing_file_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(IngestionError) as exc:
        ingest_wav(tmp_path / "missing.wav", tmp_path / "artifacts")
    assert exc.value.code == "NOT_FOUND"


def test_cli_ingest_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    code = main(["ingest", str(source), "--artifact-root", str(tmp_path / "artifacts")])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["control_baseline"] == "CONTROL_A"
    assert Path(payload["derived_working"]).is_file()


def test_cli_invalid_input_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bogus = tmp_path / "nope.bin"
    bogus.write_bytes(b"\x00\x01\x02")
    code = main(["ingest", str(bogus), "--artifact-root", str(tmp_path / "artifacts")])
    captured = capsys.readouterr()
    assert code == 2
    payload = json.loads(captured.err)
    assert payload["ok"] is False
    assert payload["error_code"] == "UNSUPPORTED_FORMAT"


def test_no_out_of_scope_capabilities_imported() -> None:
    import a2l
    import sys

    forbidden = {"demucs", "whisper", "faster_whisper", "torch"}
    loaded = {name.split(".")[0] for name in sys.modules}
    assert forbidden.isdisjoint(loaded)
    assert not hasattr(a2l, "isolate_vocals")
    assert not hasattr(a2l, "approve_lyrics")


def test_pcm_fixture_is_valid_wav() -> None:
    data = pcm_wav_bytes()
    assert data.startswith(b"RIFF")
    assert data[8:12] == b"WAVE"


def test_existing_source_is_not_rewritten(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    first = ingest_wav(source, tmp_path / "artifacts")
    stored_mtime = first.source_path.stat().st_mtime_ns
    ingest_wav(source, tmp_path / "artifacts")
    assert first.source_path.stat().st_mtime_ns == stored_mtime
    assert sha256(first.source_path) == first.source_sha256
