"""ACI-A2L-012 NVIDIA Parakeet alternate-engine workflow. Does not require NeMo."""

from __future__ import annotations

import json
from pathlib import Path

from a2l.approve import lyric_display_state
from a2l.engines import EngineResult, EngineSegment, ScriptedEngine
from a2l.ingest import ingest_wav
from a2l.pipeline import PARAKEET_PIPELINE_DIRNAME, PIPELINE_DIRNAME, TRANSCRIPTION_DIRNAME
from a2l.review import apply_corrections, load_or_create_review, save_review
from a2l.structure import structure_lyrics
from a2l.transcribe import transcribe_from_manifest
from a2l.uncertainty import QUESTIONABLE_FLAGS, evaluate_uncertainty
from tests.test_app import _engine, _multipart, _request, _start, _wait_ready
from tests.wav_fixtures import pcm_wav_bytes, write_pcm_wav


def _parakeet_engine() -> ScriptedEngine:
    return ScriptedEngine(
        EngineResult(
            technology="nvidia_nemo_parakeet",
            model="parakeet-tdt-0.6b-v2",
            text="Play something we can stomp to",
            language="en",
            segments=(
                EngineSegment(0.0, 2.0, "Play something we can stomp to", None, None, None),
            ),
            configuration={"alternate_engine_aci": "ACI-A2L-012", "confidence_signals": "none"},
        )
    )


def test_parakeet_writes_isolated_pipeline_and_does_not_touch_primary(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    before = source.read_bytes()
    ingest = ingest_wav(source, tmp_path / "artifacts")
    primary = ingest.artifact_dir / PIPELINE_DIRNAME / TRANSCRIPTION_DIRNAME
    primary.mkdir(parents=True)
    marker = primary / "transcription_draft.json"
    marker.write_text("PRIMARY_MUST_NOT_CHANGE\n", encoding="utf-8")

    result = transcribe_from_manifest(ingest.manifest_path, engine=_parakeet_engine())
    assert PARAKEET_PIPELINE_DIRNAME in result.draft_path.parts
    assert result.draft_path.parts[-3] == PARAKEET_PIPELINE_DIRNAME
    assert marker.read_text(encoding="utf-8") == "PRIMARY_MUST_NOT_CHANGE\n"
    assert ingest.source_path.read_bytes() == before
    assert result.draft["engine"]["technology"] == "nvidia_nemo_parakeet"
    assert result.draft["engine"]["model"] == "parakeet-tdt-0.6b-v2"
    assert result.draft["engine"]["architecture_status"] == "ACI-A2L-012_ALTERNATE_NVIDIA_PARAKEET_TDT_0_6B_V2"
    assert "NO_ENGINE_CONFIDENCE" in result.draft["flags"]
    assert result.draft["segments"][0]["avg_logprob"] is None
    assert "NO_ENGINE_CONFIDENCE" in result.draft["segments"][0]["flags"]
    assert "LOW_CONFIDENCE" not in result.draft["segments"][0]["flags"]
    assert result.draft["usable_as_approved_lyrics"] is False


def test_parakeet_missing_confidence_is_not_invented_as_whisper_uncertainty(tmp_path: Path) -> None:
    source = write_pcm_wav(tmp_path / "tone.wav")
    import io
    import wave

    frames = b"\x00\x10" * 4410
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(frames)
    source.write_bytes(buffer.getvalue())
    ingest = ingest_wav(source, tmp_path / "artifacts")
    transcribed = transcribe_from_manifest(ingest.manifest_path, engine=_parakeet_engine())
    report = evaluate_uncertainty(transcribed.draft_path).report
    assert "NO_ENGINE_CONFIDENCE" not in QUESTIONABLE_FLAGS
    assert "NO_ENGINE_CONFIDENCE" in report["flags"]
    assert report["items"][0]["status"] == "UNVERIFIED_MACHINE_TEXT"
    assert report["job_status"] == "UNVERIFIED_MACHINE_TEXT"
    assert report["rewritten_text"] is None
    assert report["llm_interpretation"] is False

    structured = structure_lyrics(transcribed.draft_path.parent.parent / "uncertainty" / "uncertainty_report.json").draft
    machine = next(line for line in structured["lines"] if line["kind"] == "machine_line")
    assert "NO_ENGINE_CONFIDENCE" in machine["flags"]
    assert machine["uncertain"] is False
    assert structured["transcription_engine"] == "nvidia_nemo_parakeet"
    assert structured["pipeline_dirname"] == PARAKEET_PIPELINE_DIRNAME


def test_parakeet_review_save_is_not_approval(tmp_path: Path, monkeypatch) -> None:
    artifact_root = tmp_path / "artifacts"

    def job_dir(sha=None, artifact_root=artifact_root):
        return artifact_root / "ingest" / sha

    monkeypatch.setattr("a2l.review.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", job_dir)
    source = write_pcm_wav(tmp_path / "mastered.wav")
    ingest = ingest_wav(source, artifact_root)
    transcribed = transcribe_from_manifest(ingest.manifest_path, engine=_parakeet_engine())
    uncertainty = evaluate_uncertainty(transcribed.draft_path)
    structure_lyrics(uncertainty.report_path)
    review = load_or_create_review(sha=ingest.job_id, pipeline_dirname=PARAKEET_PIPELINE_DIRNAME)
    assert review["transcription_engine"] == "nvidia_nemo_parakeet"
    assert review["transcription_model"] == "parakeet-tdt-0.6b-v2"
    assert review["pipeline_dirname"] == PARAKEET_PIPELINE_DIRNAME
    assert review["approval_status"] == "NOT_APPROVED"
    apply_corrections(review, {1: "Play something we can groove to"})
    saved = save_review(review, sha=ingest.job_id)
    assert PARAKEET_PIPELINE_DIRNAME in saved.parts
    reloaded = json.loads(saved.read_text(encoding="utf-8"))
    assert reloaded["usable_as_approved_lyrics"] is False
    assert lyric_display_state(reloaded, ingest.job_id) != "APPROVED"
    primary_review = ingest.artifact_dir / PIPELINE_DIRNAME / "human_review" / "reviewed_lyric_draft.json"
    assert not primary_review.is_file()


def test_parakeet_approved_export_is_engine_independent(tmp_path: Path, monkeypatch) -> None:
    from a2l.approve import approve_reviewed_lyrics
    from a2l.export import format_approved_export

    artifact_root = tmp_path / "artifacts"

    def job_dir(sha=None, artifact_root=artifact_root):
        return artifact_root / "ingest" / sha

    monkeypatch.setattr("a2l.review.ingest_job_dir", job_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", job_dir)
    source = write_pcm_wav(tmp_path / "mastered.wav")
    ingest = ingest_wav(source, artifact_root)
    transcribed = transcribe_from_manifest(ingest.manifest_path, engine=_parakeet_engine())
    uncertainty = evaluate_uncertainty(transcribed.draft_path)
    structure_lyrics(uncertainty.report_path)
    review = load_or_create_review(sha=ingest.job_id, pipeline_dirname=PARAKEET_PIPELINE_DIRNAME)
    apply_corrections(review, {1: "Play something we can groove to"})
    from a2l.metadata import apply_song_metadata

    apply_song_metadata(review, "Sangria", "Danni")
    save_review(review, sha=ingest.job_id)
    approved = approve_reviewed_lyrics(review, ingest.job_id, confirm=True)
    canonical = approved["txt_path"].read_text(encoding="utf-8")
    export = format_approved_export(
        ingest.job_id,
        pipeline_dirname=PARAKEET_PIPELINE_DIRNAME,
    )
    payload = json.loads(approved["json_path"].read_text(encoding="utf-8"))
    assert approved["review"]["transcription_engine"] == "nvidia_nemo_parakeet"
    assert payload["song_title"] == "Sangria"
    assert payload["artist"] == "Danni"
    assert export.text.startswith("Sangria\nDanni\n\n")
    assert export.text.endswith(canonical)
    assert "Sangria" not in canonical
    assert "Play something we can groove to" in export.text
    assert PARAKEET_PIPELINE_DIRNAME in export.source_txt.parts
    primary_approved = ingest.artifact_dir / PIPELINE_DIRNAME / "approved_lyrics" / "approved_lyrics.txt"
    assert not primary_approved.is_file()


def test_app_parakeet_selection_uses_isolated_chain(tmp_path: Path, monkeypatch) -> None:
    source = write_pcm_wav(tmp_path / "mastered.wav")
    before = source.read_bytes()
    app, server, port = _start(tmp_path, monkeypatch, engine=_parakeet_engine())
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes(), engine="nvidia-parakeet")
        status, _, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert status == 200
        session = _wait_ready(port)
        assert session["error"] == ""
        assert session["can_review"] is True
        assert session["lyric_state"] != "APPROVED"
        assert app.pipeline_dirname == PARAKEET_PIPELINE_DIRNAME

        status, data, _ = _request(port, "GET", "/api/state")
        state = json.loads(data.decode("utf-8"))
        assert status == 200
        assert state["review"]["transcription_engine"] == "nvidia_nemo_parakeet"
        assert state["review"]["transcription_model"] == "parakeet-tdt-0.6b-v2"
        assert state["lyric_state"] != "APPROVED"
        job = Path(app.artifact_root) / "ingest" / app.job_id
        assert (job / PARAKEET_PIPELINE_DIRNAME / TRANSCRIPTION_DIRNAME / "transcription_draft.json").is_file()
        assert not (job / PIPELINE_DIRNAME / TRANSCRIPTION_DIRNAME / "transcription_draft.json").is_file()
        assert source.read_bytes() == before
    finally:
        server.shutdown()


def test_faster_whisper_app_path_still_uses_primary_pipeline(tmp_path: Path, monkeypatch) -> None:
    app, server, port = _start(tmp_path, monkeypatch, engine=_engine())
    try:
        boundary, body = _multipart("demo.wav", pcm_wav_bytes(), engine="faster-whisper")
        status, _, _ = _request(
            port,
            "POST",
            "/api/extract",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert status == 200
        session = _wait_ready(port)
        assert session["error"] == ""
        assert app.pipeline_dirname == PIPELINE_DIRNAME
        job = Path(app.artifact_root) / "ingest" / app.job_id
        assert (job / PIPELINE_DIRNAME / TRANSCRIPTION_DIRNAME / "transcription_draft.json").is_file()
        assert not (job / PARAKEET_PIPELINE_DIRNAME).exists()
    finally:
        server.shutdown()


def test_app_html_exposes_engine_choice_without_redesign() -> None:
    html = (Path(__file__).resolve().parents[1] / "a2l" / "app.html").read_text(encoding="utf-8")
    assert 'id="engine"' in html
    assert "faster-whisper" in html
    assert "nvidia-parakeet" in html
    assert "NVIDIA PARAKEET / TDT-0.6B-V2" in html
    assert "FASTER-WHISPER / LARGE-V3" in html
    assert "selected" in html
