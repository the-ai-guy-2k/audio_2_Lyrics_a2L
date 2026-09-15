"""ACI-A2L-SI-012 governed Song Intelligence Record."""

from __future__ import annotations

import json
from pathlib import Path

from a2l.pipeline import LOCKED_SHA256, ROOT, ingest_job_dir
from a2l.song_intelligence import run_analysis
from a2l.song_intelligence_record import (
    ENGINEERING_PARTIAL,
    INSTRUMENTATION_DEFECT_REF,
    ORIGIN_REUSED,
    RECORD_TYPE,
    RUN_MISSING,
    RUN_NOT_RUN,
    SCHEMA_VERSION,
    load_sir,
)
from tests.test_song_intelligence import _approve, _fake_runners, _ingest, _request, _start, _wait_si


def test_sir_creation_identity_revision_and_not_run(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _approve(ingest, tmp_path)
    first = run_analysis(
        ingest.job_id,
        "key_mode",
        None,
        tmp_path / "artifacts",
        runners=_fake_runners(),
    )
    assert first["song_intelligence_record"] is True
    sir = load_sir(ingest.job_id, job_dir=ingest.artifact_dir)
    assert sir["record_type"] == RECORD_TYPE
    assert sir["schema_version"] == SCHEMA_VERSION
    assert sir["ingest_job_id"] == ingest.job_id
    assert sir["source"]["sha256"] == ingest.job_id
    assert sir["source"]["copied_into_record"] is False
    assert sir["master_copied_into_record"] is False
    assert sir["usable_as_human_approved_song_facts"] is False
    assert sir["revision"] == 1
    assert sir["song"]["title"]["value"] == "Stomp To"
    assert sir["song"]["filename_not_used_as_title"] is True
    assert sir["lyrics"]["run_state"] == RUN_NOT_RUN
    assert sir["rhythm_structure"]["run_state"] == RUN_NOT_RUN
    assert sir["audio_intelligence"]["run_state"] == RUN_NOT_RUN
    assert sir["lyric_intelligence"]["run_state"] == RUN_NOT_RUN
    assert sir["key_mode"]["run_state"] != RUN_NOT_RUN
    assert sir["key_mode"]["authority"] == "MACHINE-DERIVED"
    assert sir["key_mode"]["human_validation"] == "PENDING HUMAN VALIDATION"
    assert sir["key_mode"]["confidence"]["calibrated_probability"] is False
    assert sir["lyrics"]["engineering_validation"] == "NOT RUN"
    second = run_analysis(
        ingest.job_id,
        "rhythm_structure",
        None,
        tmp_path / "artifacts",
        runners=_fake_runners(),
    )
    assert second["revision"] == 2
    sir = load_sir(ingest.job_id, job_dir=ingest.artifact_dir)
    assert sir["revision"] == 2
    assert sir["key_mode"]["result_origin"] == ORIGIN_REUSED
    assert sir["key_mode"]["reused_from_revision"] == 1
    assert sir["rhythm_structure"]["result_origin"] == "GENERATED"
    history = ingest.artifact_dir / "song_intelligence_record_history" / "r1.json"
    assert history.is_file()
    prior = json.loads(history.read_text(encoding="utf-8"))
    assert prior["revision"] == 1
    source_bytes = (ingest.artifact_dir / "authoritative_source" / "source.wav").read_bytes()
    assert sir["source"]["master_hash_unchanged"] is True
    assert (ingest.artifact_dir / "authoritative_source" / "source.wav").read_bytes() == source_bytes


def test_sir_full_run_preserves_partial_and_defect(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _approve(ingest, tmp_path)
    run_analysis(
        ingest.job_id,
        "full_song_intelligence",
        None,
        tmp_path / "artifacts",
        runners=_fake_runners(),
    )
    sir = load_sir(ingest.job_id, job_dir=ingest.artifact_dir)
    assert sir["lyrics"]["approval_state"] == "APPROVED"
    assert sir["lyrics"]["approved_lyric_revision"] == 1
    assert "approved_lyrics.json" in (sir["lyrics"].get("approved_lyric_artifact_ref") or "")
    assert sir["lyrics"]["canonical_lyrics_remain_authoritative"] is True
    audio = sir["audio_intelligence"]
    assert audio["engineering_validation"] == ENGINEERING_PARTIAL
    assert audio["categories"]["vocal_characteristics"]["engineering_validation"] == ENGINEERING_PARTIAL
    assert audio["categories"]["instrumentation"]["engineering_validation"] == ENGINEERING_PARTIAL
    assert audio["categories"]["instrumentation"]["defect_ref"] == INSTRUMENTATION_DEFECT_REF
    assert audio["categories"]["instrumentation"]["defect_disposition"] == "DEFERRED TO BUG-FIX LANE"
    assert sir["lyric_intelligence"]["interpretive_authority"] == "MACHINE-DERIVED"
    assert sir["lyric_intelligence"]["artist_approved_interpretation"] is False
    assert sir["key_mode"]["provenance"]["source_aci"] == "ACI-A2L-SI-004"
    aggregation = json.loads((ingest.artifact_dir / "song_intelligence_ui" / "ui_aggregation.json").read_text(encoding="utf-8"))
    assert aggregation["kind"] == "TEMPORARY_UI_AGGREGATION"
    assert aggregation["outranks_sir"] is False


def test_missing_metadata_stays_missing(tmp_path: Path, monkeypatch) -> None:
    from a2l.ingest import ingest_wav
    from tests.wav_fixtures import write_pcm_wav

    wav = tmp_path / "file-name-is-not-the-title.wav"
    write_pcm_wav(wav)
    ingest = ingest_wav(wav, tmp_path / "artifacts")
    monkeypatch.setattr("a2l.review.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    monkeypatch.setattr("a2l.approve.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    monkeypatch.setattr("a2l.pipeline.ingest_job_dir", lambda sha=None, artifact_root=None: ingest.artifact_dir)
    run_analysis(
        ingest.job_id,
        "key_mode",
        None,
        tmp_path / "artifacts",
        runners=_fake_runners(),
    )
    sir = load_sir(ingest.job_id, job_dir=ingest.artifact_dir)
    assert sir["song"]["title"]["status"] == RUN_MISSING
    assert not sir["song"]["title"]["value"]
    assert sir["song"]["primary_artist"]["status"] == RUN_MISSING
    assert sir["song"]["filename_not_used_as_title"] is True


def test_ui_consumes_governed_sir(tmp_path: Path, monkeypatch) -> None:
    ingest = _ingest(tmp_path, monkeypatch)
    _approve(ingest, tmp_path)
    _app, server, port, _root = _start(tmp_path, monkeypatch)
    try:
        _request(
            port,
            "POST",
            "/api/song-intelligence",
            body=json.dumps({"ingest_job_id": ingest.job_id, "capability": "full_song_intelligence"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        result = _wait_si(port)
        assert result["kind"] == RECORD_TYPE
        status, data, _ = _request(port, "GET", f"/api/song-intelligence?ingest_job_id={ingest.job_id}")
        loaded = json.loads(data.decode("utf-8"))
        assert status == 200
        assert loaded["song_intelligence_record"] is True
        assert loaded["revision"] == result["revision"]
        html = _request(port, "GET", "/")[1].decode("utf-8")
        assert "governed Song Intelligence Record" in html
        assert "Full Song Intelligence" in html
        assert "Analyze song" in html
        assert "Extract lyrics" in html
    finally:
        server.shutdown()


def test_jay_source_identity_without_heavyweight_rerun() -> None:
    job_dir = ingest_job_dir(LOCKED_SHA256)
    source = job_dir / "authoritative_source" / "source.wav"
    if not source.is_file():
        return
    from a2l.song_intelligence import sha256_file
    from a2l.song_intelligence_engines import _field, run_lyric_intelligence, run_lyrics_workflow
    from a2l.song_intelligence import STATUS_COMPLETE, STATUS_PARTIAL

    digest = sha256_file(source)
    assert digest == LOCKED_SHA256
    after = sha256_file(source)
    assert after == digest
    evidence = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-004-evidence" / "key_mode_raw.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["source_sha256_before"] == LOCKED_SHA256
    assert payload["source_sha256_after"] == LOCKED_SHA256
    assert payload["ingest_source_sha256_after"] == LOCKED_SHA256

    rhythm_path = "docs/nebula/artifacts/aci-a2l-si-002-evidence/all_in_one_raw.json"
    key_path = "docs/nebula/artifacts/aci-a2l-si-004-evidence/key_mode_raw.json"
    clap_path = "docs/nebula/artifacts/aci-a2l-si-008-evidence/classification_resolution_raw.json"
    ast_path = "docs/nebula/artifacts/aci-a2l-si-009-evidence/instrumentation_genre_raw.json"
    panns_path = "docs/nebula/artifacts/aci-a2l-si-010-evidence/instrument_presence_raw.json"
    rhythm = json.loads((ROOT / rhythm_path).read_text(encoding="utf-8"))
    key_mode = payload["key_mode"]
    summary = rhythm["rhythm_structure"]
    structure = [item.get("display") or item.get("label") for item in (summary.get("segments") or [])]

    def reused(engine_id, status, fields, artifact_ref):
        def runner(_song):
            return {
                "status": status,
                "message": "",
                "result_origin": ORIGIN_REUSED,
                "source_artifact_ref": artifact_ref,
                "fields": fields,
            }

        return runner

    runners = {
        "lyrics_workflow": run_lyrics_workflow,
        "lyric_intelligence": run_lyric_intelligence,
        "rhythm_structure": reused(
            "rhythm_structure",
            STATUS_COMPLETE,
            [
                _field(
                    "bpm",
                    "music",
                    "BPM",
                    summary.get("bpm"),
                    engine_id="rhythm_structure",
                    engine_label="Rhythm + Structure Analyzer",
                    engine_technical="All-In-One / Harmonix (all-in-one-infer, mix-as-stems)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    evidence=[{"beats": summary.get("beats_count"), "downbeats": summary.get("downbeats_count")}],
                    note="Reused SI-002 evidence. Mix-as-stems Harmonix path only.",
                ),
                _field(
                    "rhythm_evidence",
                    "music",
                    "Beat / downbeat evidence",
                    f"{summary.get('beats_count')} beats, {summary.get('downbeats_count')} downbeats",
                    engine_id="rhythm_structure",
                    engine_label="Rhythm + Structure Analyzer",
                    engine_technical="All-In-One / Harmonix (all-in-one-infer, mix-as-stems)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    note="Beat list retained in SI-002 evidence; SIR stores the summary/reference.",
                ),
                _field(
                    "structure",
                    "music",
                    "Song structure",
                    structure,
                    engine_id="rhythm_structure",
                    engine_label="Rhythm + Structure Analyzer",
                    engine_technical="All-In-One / Harmonix (all-in-one-infer, mix-as-stems)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                ),
            ],
            rhythm_path,
        ),
        "key_mode": reused(
            "key_mode",
            STATUS_COMPLETE,
            [
                _field(
                    "key",
                    "music",
                    "Key",
                    key_mode.get("key"),
                    engine_id="key_mode",
                    engine_label="Key + Mode Analyzer",
                    engine_technical="librosa chroma_cqt + Krumhansl–Kessler / Krumhansl–Schmuckler",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    evidence=[
                        {"label": "score", "value": key_mode.get("score")},
                        {
                            "label": "alternates",
                            "value": [
                                f"{item.get('key')} {item.get('mode')} ({item.get('score')})"
                                for item in (key_mode.get("alternates") or [])[:5]
                            ],
                        },
                    ],
                    note="Reused SI-004 evidence. Score is not a calibrated probability.",
                ),
                _field(
                    "mode",
                    "music",
                    "Mode",
                    key_mode.get("mode"),
                    engine_id="key_mode",
                    engine_label="Key + Mode Analyzer",
                    engine_technical="librosa chroma_cqt + Krumhansl–Kessler / Krumhansl–Schmuckler",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    note="Reused SI-004 evidence. Musical validation is pending Jay.",
                ),
            ],
            key_path,
        ),
        "clap_audio": reused(
            "clap_audio",
            STATUS_PARTIAL,
            [
                _field(
                    "energy",
                    "sound",
                    "Energy / Intensity",
                    "HIGH ENERGY",
                    engine_id="clap_audio",
                    engine_label="Audio Intelligence (CLAP)",
                    engine_technical="LAION CLAP with deterministic RMS/onset energy",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    note="Reused SI-007 evidence. Energy label is machine-derived from measured RMS.",
                ),
                _field(
                    "acoustic_electronic",
                    "sound",
                    "Acoustic / Electronic",
                    "electric / electronic-leaning",
                    engine_id="clap_audio",
                    engine_label="Audio Intelligence (CLAP)",
                    engine_technical="CLAP CONTROL (SI-007/SI-008)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    note="Reused SI-008 evidence. CLAP cosine ranking, not a calibrated probability.",
                ),
                _field(
                    "vocal_character",
                    "sound",
                    "Vocal Characteristics",
                    "ensemble / mixed vocal character",
                    engine_id="clap_audio",
                    engine_label="Audio Intelligence (CLAP)",
                    engine_technical="CLAP ensemble (SI-008)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_PARTIAL,
                    note="Reused SI-008 evidence. Partial. Not an authoritative vocal fact.",
                ),
            ],
            clap_path,
        ),
        "ast_genre": reused(
            "ast_genre",
            STATUS_COMPLETE,
            [
                _field(
                    "genre_style",
                    "sound",
                    "Genre / Style",
                    "Grunge / rock family",
                    engine_id="ast_genre",
                    engine_label="Genre / Style",
                    engine_technical="AST (MIT/ast-finetuned-audioset-10-10-0.4593)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_COMPLETE,
                    note="Reused SI-009 evidence. AST scores are ranking scores, not calibrated probabilities.",
                )
            ],
            ast_path,
        ),
        "panns_instrumentation": reused(
            "panns_instrumentation",
            STATUS_PARTIAL,
            [
                _field(
                    "instrumentation",
                    "sound",
                    "Instrumentation",
                    "Guitar, Electric guitar, Acoustic guitar",
                    engine_id="panns_instrumentation",
                    engine_label="Instrumentation",
                    engine_technical="PANNs Cnn14 (Cnn14_mAP=0.431.pth)",
                    authority="MACHINE-DERIVED",
                    status=STATUS_PARTIAL,
                    note=(
                        "Reused SI-010 evidence. Partial. Not an Engineering WIN. "
                        f"Known defect: {INSTRUMENTATION_DEFECT_REF}. Deferred to the bug-fix lane."
                    ),
                )
            ],
            panns_path,
        ),
    }
    before = source.read_bytes()
    display = run_analysis(LOCKED_SHA256, "full_song_intelligence", None, ROOT / "artifacts", runners=runners)
    assert display["song_intelligence_record"] is True
    sir = load_sir(LOCKED_SHA256, job_dir=job_dir)
    assert sir["source"]["sha256"] == LOCKED_SHA256
    assert sir["rhythm_structure"]["result_origin"] == ORIGIN_REUSED
    assert sir["key_mode"]["estimated_key"] == "A"
    assert sir["audio_intelligence"]["categories"]["instrumentation"]["defect_ref"] == INSTRUMENTATION_DEFECT_REF
    assert sir["lyric_intelligence"]["run_state"] != RUN_NOT_RUN
    assert source.read_bytes() == before
    assert sha256_file(source) == LOCKED_SHA256
    assert display["revision"] >= 1

