"""ACI-A2L-SI-012 governed Song Intelligence Record.

This record is current truth about what A2L knows. Contained
MACHINE-DERIVED values are not human-approved musical facts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from a2l.errors import SongIntelligenceError
from a2l.pipeline import ingest_job_dir

RECORD_TYPE = "SONG_INTELLIGENCE_RECORD"
SCHEMA_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-SI-012"
RECORD_FILENAME = "song_intelligence_record.json"
HISTORY_DIRNAME = "song_intelligence_record_history"
AUTHORITY_OF_RECORD = "GOVERNED_CURRENT_TRUTH"
INSTRUMENTATION_DEFECT_REF = "docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md"
INSTRUMENTATION_DEFECT_DISPOSITION = "DEFERRED TO BUG-FIX LANE"

RUN_NOT_RUN = "NOT_RUN"
RUN_AVAILABLE = "AVAILABLE"
RUN_PARTIAL = "PARTIAL"
RUN_UNAVAILABLE = "UNAVAILABLE"
RUN_FAILED = "FAILED"
RUN_MISSING = "MISSING"

ORIGIN_GENERATED = "GENERATED"
ORIGIN_REUSED = "REUSED"
ORIGIN_NOT_RUN = "NOT_RUN"

STATUS_COMPLETE = "Complete"
STATUS_PARTIAL = "Partial"
STATUS_UNAVAILABLE = "Unavailable"
STATUS_FAILED = "Failed"
STATUS_NOT_RUN = "Not run"

ENGINEERING_WIN = "ENGINEERING WIN"
ENGINEERING_PARTIAL = "PARTIAL"
ENGINEERING_NOT_RUN = "NOT RUN"
HUMAN_PENDING = "PENDING HUMAN VALIDATION"
HUMAN_NOT_APPLICABLE = "NOT APPLICABLE"

SECTION_ENGINES = {
    "lyrics": ("lyrics_workflow",),
    "rhythm_structure": ("rhythm_structure",),
    "key_mode": ("key_mode",),
    "audio_intelligence": ("clap_audio", "ast_genre", "panns_instrumentation"),
    "lyric_intelligence": ("lyric_intelligence",),
}

ENGINE_PROVENANCE = {
    "lyrics_workflow": {
        "capability": "Lyrics",
        "analyzer_id": "lyrics_workflow",
        "method": "Existing A2L lyric transcription and approval workflow",
        "model_or_checkpoint": None,
        "source_aci": "ACI-A2L-008",
    },
    "rhythm_structure": {
        "capability": "Rhythm + Structure",
        "analyzer_id": "rhythm_structure",
        "method": "All-In-One / Harmonix mix-as-stems",
        "model_or_checkpoint": "harmonix-all",
        "source_aci": "ACI-A2L-SI-002",
    },
    "key_mode": {
        "capability": "Key + Mode",
        "analyzer_id": "key_mode",
        "method": "librosa chroma_cqt + Krumhansl–Kessler / Krumhansl–Schmuckler",
        "model_or_checkpoint": None,
        "source_aci": "ACI-A2L-SI-004",
        "score_kind": "chroma profile correlation; not a calibrated probability",
    },
    "clap_audio": {
        "capability": "Audio Intelligence",
        "analyzer_id": "clap_audio",
        "method": "LAION CLAP with deterministic RMS/onset energy",
        "model_or_checkpoint": "laion/larger_clap_music",
        "source_aci": "ACI-A2L-SI-007",
    },
    "ast_genre": {
        "capability": "Audio Intelligence",
        "analyzer_id": "ast_genre",
        "method": "AST AudioSet ranking",
        "model_or_checkpoint": "MIT/ast-finetuned-audioset-10-10-0.4593",
        "source_aci": "ACI-A2L-SI-009",
    },
    "panns_instrumentation": {
        "capability": "Audio Intelligence",
        "analyzer_id": "panns_instrumentation",
        "method": "PANNs Cnn14 clipwise mean",
        "model_or_checkpoint": "Cnn14_mAP=0.431.pth",
        "source_aci": "ACI-A2L-SI-010",
    },
    "lyric_intelligence": {
        "capability": "Lyric Intelligence",
        "analyzer_id": "lyric_intelligence",
        "method": "Deterministic in-repo NLP on AUTHORITATIVE APPROVED LYRICS",
        "model_or_checkpoint": None,
        "source_aci": "ACI-A2L-SI-006",
    },
}

AUDIO_CATEGORY_ENGINES = {
    "energy_intensity": "clap_audio",
    "acoustic_electronic": "clap_audio",
    "vocal_characteristics": "clap_audio",
    "genre_style": "ast_genre",
    "instrumentation": "panns_instrumentation",
}

AUDIO_ENGINEERING = {
    "energy_intensity": ENGINEERING_WIN,
    "acoustic_electronic": ENGINEERING_WIN,
    "genre_style": ENGINEERING_WIN,
    "vocal_characteristics": ENGINEERING_PARTIAL,
    "instrumentation": ENGINEERING_PARTIAL,
}


def default_sir_path(sha: str, job_dir: str | Path | None = None, artifact_root: str | Path | None = None) -> Path:
    return _job_root(sha, job_dir, artifact_root) / RECORD_FILENAME


def history_dir(sha: str, job_dir: str | Path | None = None, artifact_root: str | Path | None = None) -> Path:
    return _job_root(sha, job_dir, artifact_root) / HISTORY_DIRNAME


def load_sir(sha: str, job_dir: str | Path | None = None, artifact_root: str | Path | None = None) -> dict | None:
    path = default_sir_path(sha, job_dir=job_dir, artifact_root=artifact_root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SongIntelligenceError("SIR_INVALID", "song_intelligence_record.json is not valid JSON.") from exc
    if payload.get("record_type") != RECORD_TYPE:
        raise SongIntelligenceError("SIR_INVALID", "song_intelligence_record.json is not a Song Intelligence Record.")
    return payload


def persist_sir_from_run(song: dict, run: dict, now: str | None = None) -> dict:
    """Write the current governed SIR from one analysis run, preserving prior sections."""
    job = song["ingest_job_id"]
    job_dir = song["job_dir"]
    previous = load_sir(job, job_dir=job_dir)
    generated_at = now or datetime.now(timezone.utc).isoformat()
    record = assemble_sir(song, run, previous=previous, generated_at=generated_at)
    path = default_sir_path(job, job_dir=job_dir)
    if previous:
        archive = history_dir(job, job_dir=job_dir)
        archive.mkdir(parents=True, exist_ok=True)
        prior_rev = int(previous.get("revision") or 1)
        (archive / f"r{prior_rev}.json").write_text(json.dumps(previous, indent=2) + "\n", encoding="utf-8")
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def assemble_sir(song: dict, run: dict, previous: dict | None = None, generated_at: str | None = None) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    executed = list(run.get("engines_requested") or [])
    fields_by_engine = _fields_by_engine(run.get("fields") or [])
    modules = {item["id"]: item for item in (run.get("modules") or [])}
    created_at = (previous or {}).get("created_at") or generated_at
    revision = int((previous or {}).get("revision") or 0) + 1
    history = list((previous or {}).get("revision_history") or [])
    if previous:
        history.append(
            {
                "revision": previous.get("revision"),
                "updated_at": previous.get("updated_at"),
                "capability": (previous.get("this_run") or {}).get("capability"),
                "engines_requested": (previous.get("this_run") or {}).get("engines_requested") or [],
                "record_ref": f"ingest/{song['ingest_job_id']}/{HISTORY_DIRNAME}/r{previous.get('revision')}.json",
            }
        )
    lyrics = _section_from_engines(
        "lyrics",
        executed,
        fields_by_engine,
        modules,
        previous.get("lyrics") if previous else None,
        previous_revision=(previous or {}).get("revision"),
        generated_at=generated_at,
        extra=_lyrics_extra(song, executed),
        engineering=_lyrics_engineering(song, executed, modules),
        authority=_lyrics_authority(song, executed),
        human_validation=HUMAN_NOT_APPLICABLE,
    )
    rhythm = _section_from_engines(
        "rhythm_structure",
        executed,
        fields_by_engine,
        modules,
        previous.get("rhythm_structure") if previous else None,
        previous_revision=(previous or {}).get("revision"),
        generated_at=generated_at,
        engineering=ENGINEERING_WIN,
        authority="MACHINE-DERIVED",
        human_validation=HUMAN_PENDING,
    )
    key_mode = _section_from_engines(
        "key_mode",
        executed,
        fields_by_engine,
        modules,
        previous.get("key_mode") if previous else None,
        previous_revision=(previous or {}).get("revision"),
        generated_at=generated_at,
        engineering=ENGINEERING_WIN,
        authority="MACHINE-DERIVED",
        human_validation=HUMAN_PENDING,
        extra=_key_mode_extra(fields_by_engine.get("key_mode") or []),
    )
    audio = _audio_section(
        executed,
        fields_by_engine,
        modules,
        previous.get("audio_intelligence") if previous else None,
        previous_revision=(previous or {}).get("revision"),
        generated_at=generated_at,
    )
    lyric_intel = _section_from_engines(
        "lyric_intelligence",
        executed,
        fields_by_engine,
        modules,
        previous.get("lyric_intelligence") if previous else None,
        previous_revision=(previous or {}).get("revision"),
        generated_at=generated_at,
        engineering=ENGINEERING_WIN,
        authority="MACHINE-DERIVED",
        human_validation=HUMAN_PENDING,
        extra=_lyric_intel_extra(fields_by_engine.get("lyric_intelligence") or [], song),
    )
    source_ref = f"ingest/{song['ingest_job_id']}/authoritative_source/source.wav"
    return {
        "record_type": RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "producer_aci": PRODUCER_ACI,
        "authority_of_record": AUTHORITY_OF_RECORD,
        "usable_as_human_approved_song_facts": False,
        "master_copied_into_record": False,
        "ingest_job_id": song["ingest_job_id"],
        "revision": revision,
        "created_at": created_at,
        "updated_at": generated_at,
        "source": {
            "reference": source_ref,
            "sha256": song.get("source_sha256"),
            "copied_into_record": False,
            "master_hash_unchanged": run.get("master_hash_unchanged"),
        },
        "song": _song_section(song),
        "lyrics": lyrics,
        "rhythm_structure": rhythm,
        "key_mode": key_mode,
        "audio_intelligence": audio,
        "lyric_intelligence": lyric_intel,
        "this_run": {
            "capability": run.get("capability"),
            "engines_requested": executed,
            "engines_executed": executed,
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at") or generated_at,
            "analysis_seconds": run.get("analysis_seconds"),
            "peak_memory_bytes": run.get("peak_memory_bytes"),
            "result_origin": ORIGIN_GENERATED,
        },
        "revision_history": history,
        "notes": [
            "This record authoritatively states what A2L currently knows.",
            "MACHINE-DERIVED values are not human-approved musical facts.",
            "PARTIAL is not complete. NOT RUN is not failure. MISSING is not zero.",
            "Temporary UI aggregation does not outrank this record.",
        ],
    }


def display_payload_from_sir(record: dict, busy: bool = False) -> dict:
    fields = list(_song_display_fields(record.get("song") or {}))
    modules = []
    for section_id, engines in SECTION_ENGINES.items():
        section = record.get(section_id) or {}
        if section_id == "audio_intelligence":
            modules.extend(_audio_modules(section))
            fields.extend(section.get("fields") or [])
            for category in (section.get("categories") or {}).values():
                fields.extend(category.get("fields") or [])
            continue
        modules.append(
            {
                "id": engines[0],
                "label": (ENGINE_PROVENANCE.get(engines[0]) or {}).get("capability") or engines[0],
                "technical": (ENGINE_PROVENANCE.get(engines[0]) or {}).get("method") or "",
                "status": _display_status(section.get("run_state")),
                "message": section.get("message") or "",
                "result_origin": section.get("result_origin"),
            }
        )
        if section.get("run_state") == RUN_NOT_RUN:
            fields.append(_not_run_field(engines[0], section_id))
        else:
            fields.extend(section.get("fields") or [])
    fields.append(_record_provenance_field(record))
    song = record.get("song") or {}
    return {
        "ok": True,
        "available": True,
        "busy": busy,
        "kind": RECORD_TYPE,
        "song_intelligence_record": True,
        "usable_as_song_facts": False,
        "producer_aci": record.get("producer_aci") or PRODUCER_ACI,
        "schema_version": record.get("schema_version") or SCHEMA_VERSION,
        "revision": record.get("revision"),
        "ingest_job_id": record.get("ingest_job_id"),
        "governed_record_ref": f"ingest/{record.get('ingest_job_id')}/{RECORD_FILENAME}",
        "status": _overall_display_status(record),
        "current_engine": None,
        "capability": (record.get("this_run") or {}).get("capability"),
        "engines_requested": (record.get("this_run") or {}).get("engines_requested") or [],
        "modules": modules,
        "groups": {
            "song": {"id": "song", "label": "Song", "visible": True},
            "lyrics": {"id": "lyrics", "label": "Lyrics", "visible": True},
            "music": {"id": "music", "label": "Music Analysis", "visible": True},
            "sound": {"id": "sound", "label": "Audio / Sound Analysis", "visible": True},
            "meaning": {"id": "meaning", "label": "Lyric Meaning", "visible": True},
            "provenance": {"id": "provenance", "label": "Provenance / Authority", "visible": True},
        },
        "fields": fields,
        "song": {
            "title": (song.get("title") or {}).get("value"),
            "artist": (song.get("primary_artist") or {}).get("value"),
            "duration_seconds": (song.get("duration_seconds") or {}).get("value"),
        },
        "error": "",
        "analysis_seconds": (record.get("this_run") or {}).get("analysis_seconds"),
        "peak_memory_bytes": (record.get("this_run") or {}).get("peak_memory_bytes"),
        "master_hash_unchanged": (record.get("source") or {}).get("master_hash_unchanged"),
        "notes": record.get("notes") or [],
        "temporary_ui_aggregation": {
            "kind": "TEMPORARY_UI_AGGREGATION",
            "outranks_sir": False,
            "disposition": "DERIVED_UI_CACHE",
        },
    }


def _job_root(sha: str, job_dir: str | Path | None, artifact_root: str | Path | None) -> Path:
    if job_dir is not None:
        return Path(job_dir)
    if artifact_root is not None:
        return Path(artifact_root) / "ingest" / sha
    return ingest_job_dir(sha)


def _fields_by_engine(fields: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in fields:
        engine_id = item.get("engine_id") or ""
        if engine_id in {"song_identity"}:
            continue
        grouped.setdefault(engine_id, []).append(item)
    return grouped


def _section_from_engines(
    section_id: str,
    executed: list[str],
    fields_by_engine: dict,
    modules: dict,
    previous: dict | None,
    previous_revision,
    generated_at: str,
    *,
    engineering: str,
    authority: str | None,
    human_validation: str,
    extra: dict | None = None,
) -> dict:
    engines = SECTION_ENGINES[section_id]
    ran = any(engine_id in executed for engine_id in engines)
    if not ran:
        if previous and previous.get("run_state") not in {None, RUN_NOT_RUN}:
            reused = json.loads(json.dumps(previous))
            reused["result_origin"] = ORIGIN_REUSED
            reused["reused_from_revision"] = previous_revision
            reused["reuse_note"] = "Prior governed result kept. This analysis did not rerun this category."
            return reused
        return _not_run_section(engines[0], engineering_if_run=engineering)
    fields = []
    for engine_id in engines:
        fields.extend(fields_by_engine.get(engine_id) or [])
    statuses = [modules.get(engine_id, {}).get("status") for engine_id in engines if engine_id in executed]
    run_state = _run_state_from_statuses(statuses)
    messages = [modules.get(engine_id, {}).get("message") or "" for engine_id in engines if engine_id in executed]
    origin = ORIGIN_GENERATED
    source_ref = None
    for engine_id in engines:
        if engine_id not in executed:
            continue
        if modules.get(engine_id, {}).get("result_origin") == ORIGIN_REUSED:
            origin = ORIGIN_REUSED
            source_ref = modules.get(engine_id, {}).get("source_artifact_ref")
    section = {
        "run_state": run_state,
        "engineering_validation": _engineering_for_run(engineering, run_state),
        "human_validation": human_validation if run_state in {RUN_AVAILABLE, RUN_PARTIAL} else HUMAN_NOT_APPLICABLE,
        "authority": authority,
        "result_origin": origin,
        "reused_from_revision": None,
        "analyzed_at": generated_at,
        "provenance": _provenance_for(engines[0], generated_at),
        "fields": fields,
        "message": next((item for item in messages if item), ""),
    }
    if source_ref:
        section["provenance"]["source_artifact_ref"] = source_ref
    if extra:
        section.update(extra)
    return section


def _audio_section(executed, fields_by_engine, modules, previous, previous_revision, generated_at) -> dict:
    audio_engines = SECTION_ENGINES["audio_intelligence"]
    ran = any(engine_id in executed for engine_id in audio_engines)
    if not ran:
        if previous and previous.get("run_state") not in {None, RUN_NOT_RUN}:
            reused = json.loads(json.dumps(previous))
            reused["result_origin"] = ORIGIN_REUSED
            reused["reused_from_revision"] = previous_revision
            reused["reuse_note"] = "Prior governed Audio Intelligence kept. This analysis did not rerun it."
            return reused
        return _empty_audio_not_run()
    categories = {}
    prior_categories = (previous or {}).get("categories") or {}
    for category_id, engine_id in AUDIO_CATEGORY_ENGINES.items():
        if engine_id in executed:
            cat_fields = [
                item
                for item in (fields_by_engine.get(engine_id) or [])
                if _field_matches_category(item, category_id)
            ]
            status = (modules.get(engine_id) or {}).get("status")
            origin = (modules.get(engine_id) or {}).get("result_origin") or ORIGIN_GENERATED
            categories[category_id] = {
                "run_state": _run_state_from_statuses([status]),
                "engineering_validation": AUDIO_ENGINEERING[category_id],
                "human_validation": HUMAN_PENDING,
                "authority": "MACHINE-DERIVED",
                "result_origin": origin,
                "analyzed_at": generated_at,
                "provenance": _provenance_for(engine_id, generated_at),
                "fields": cat_fields,
            }
            source_ref = (modules.get(engine_id) or {}).get("source_artifact_ref")
            if source_ref:
                categories[category_id]["provenance"]["source_artifact_ref"] = source_ref
            if category_id == "instrumentation":
                categories[category_id]["defect_ref"] = INSTRUMENTATION_DEFECT_REF
                categories[category_id]["defect_disposition"] = INSTRUMENTATION_DEFECT_DISPOSITION
                categories[category_id]["engineering_validation"] = ENGINEERING_PARTIAL
        elif prior_categories.get(category_id) and prior_categories[category_id].get("run_state") not in {
            None,
            RUN_NOT_RUN,
        }:
            reused = json.loads(json.dumps(prior_categories[category_id]))
            reused["result_origin"] = ORIGIN_REUSED
            reused["reused_from_revision"] = previous_revision
            categories[category_id] = reused
        else:
            categories[category_id] = _not_run_audio_category(category_id)
    states = [item.get("run_state") for item in categories.values()]
    if RUN_PARTIAL in states or any(AUDIO_ENGINEERING[key] == ENGINEERING_PARTIAL and categories[key]["run_state"] != RUN_NOT_RUN for key in categories):
        overall = RUN_PARTIAL
        engineering = ENGINEERING_PARTIAL
    elif all(item == RUN_NOT_RUN for item in states):
        overall = RUN_NOT_RUN
        engineering = ENGINEERING_NOT_RUN
    elif RUN_FAILED in states and not any(item in {RUN_AVAILABLE, RUN_PARTIAL} for item in states):
        overall = RUN_FAILED
        engineering = ENGINEERING_PARTIAL
    else:
        overall = RUN_PARTIAL if RUN_UNAVAILABLE in states else RUN_AVAILABLE
        engineering = ENGINEERING_PARTIAL
    return {
        "run_state": overall,
        "engineering_validation": engineering,
        "human_validation": HUMAN_PENDING if overall in {RUN_AVAILABLE, RUN_PARTIAL} else HUMAN_NOT_APPLICABLE,
        "authority": "MACHINE-DERIVED",
        "result_origin": ORIGIN_GENERATED,
        "reused_from_revision": None,
        "analyzed_at": generated_at,
        "overall_note": "PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD",
        "categories": categories,
        "fields": [],
        "message": "",
    }


def _field_matches_category(field: dict, category_id: str) -> bool:
    field_id = field.get("id") or ""
    label = field.get("label") or ""
    mapping = {
        "energy_intensity": ("energy",),
        "acoustic_electronic": ("acoustic_electronic",),
        "vocal_characteristics": ("vocal_character", "clap_audio"),
        "genre_style": ("genre_style", "ast_genre"),
        "instrumentation": ("instrumentation", "panns_instrumentation"),
    }
    if field_id in mapping.get(category_id, ()):
        return True
    if category_id == "energy_intensity" and "Energy" in label:
        return True
    if category_id == "instrumentation" and field_id.startswith("panns"):
        return True
    return False


def _not_run_section(engine_id: str, engineering_if_run: str) -> dict:
    return {
        "run_state": RUN_NOT_RUN,
        "engineering_validation": ENGINEERING_NOT_RUN,
        "human_validation": HUMAN_NOT_APPLICABLE,
        "authority": None,
        "result_origin": ORIGIN_NOT_RUN,
        "reused_from_revision": None,
        "analyzed_at": None,
        "provenance": _provenance_for(engine_id, None),
        "fields": [],
        "message": "Not run",
        "engineering_if_run": engineering_if_run,
    }


def _not_run_audio_category(category_id: str) -> dict:
    payload = {
        "run_state": RUN_NOT_RUN,
        "engineering_validation": ENGINEERING_NOT_RUN,
        "human_validation": HUMAN_NOT_APPLICABLE,
        "authority": None,
        "result_origin": ORIGIN_NOT_RUN,
        "fields": [],
        "engineering_if_run": AUDIO_ENGINEERING[category_id],
    }
    if category_id == "instrumentation":
        payload["defect_ref"] = INSTRUMENTATION_DEFECT_REF
        payload["defect_disposition"] = INSTRUMENTATION_DEFECT_DISPOSITION
    return payload


def _empty_audio_not_run() -> dict:
    return {
        "run_state": RUN_NOT_RUN,
        "engineering_validation": ENGINEERING_NOT_RUN,
        "human_validation": HUMAN_NOT_APPLICABLE,
        "authority": None,
        "result_origin": ORIGIN_NOT_RUN,
        "overall_note": "PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD",
        "categories": {key: _not_run_audio_category(key) for key in AUDIO_CATEGORY_ENGINES},
        "fields": [],
        "message": "Not run",
    }


def _run_state_from_statuses(statuses: list) -> str:
    values = [item for item in statuses if item]
    if not values:
        return RUN_NOT_RUN
    if all(item == STATUS_UNAVAILABLE for item in values):
        return RUN_UNAVAILABLE
    if all(item == STATUS_FAILED for item in values):
        return RUN_FAILED
    if STATUS_PARTIAL in values:
        return RUN_PARTIAL
    if STATUS_FAILED in values or STATUS_UNAVAILABLE in values:
        return RUN_PARTIAL
    if all(item == STATUS_COMPLETE for item in values):
        return RUN_AVAILABLE
    return RUN_PARTIAL


def _engineering_for_run(engineering: str, run_state: str) -> str:
    if run_state == RUN_NOT_RUN:
        return ENGINEERING_NOT_RUN
    if run_state == RUN_UNAVAILABLE:
        return RUN_UNAVAILABLE
    if run_state == RUN_FAILED:
        return RUN_FAILED
    if run_state == RUN_PARTIAL:
        return ENGINEERING_PARTIAL
    return engineering


def _provenance_for(engine_id: str, analyzed_at: str | None) -> dict:
    spec = ENGINE_PROVENANCE.get(engine_id) or {}
    payload = {
        "capability": spec.get("capability"),
        "analyzer_id": spec.get("analyzer_id") or engine_id,
        "method": spec.get("method"),
        "model_or_checkpoint": spec.get("model_or_checkpoint"),
        "library_version": None,
        "source_aci": spec.get("source_aci"),
        "source_artifact_ref": None,
        "analyzed_at": analyzed_at,
    }
    if spec.get("score_kind"):
        payload["score_kind"] = spec["score_kind"]
        payload["calibrated_probability"] = False
    return payload


def _song_section(song: dict) -> dict:
    title = song.get("song_title")
    artist = song.get("artist")
    duration = song.get("duration_seconds")
    return {
        "title": {
            "value": title,
            "status": RUN_AVAILABLE if title else RUN_MISSING,
            "authority": "AUTHORITATIVE INPUT" if title else RUN_MISSING,
        },
        "primary_artist": {
            "value": artist,
            "status": RUN_AVAILABLE if artist else RUN_MISSING,
            "authority": "AUTHORITATIVE INPUT" if artist else RUN_MISSING,
        },
        "duration_seconds": {
            "value": duration,
            "status": RUN_AVAILABLE if duration is not None else RUN_MISSING,
            "authority": "MEASURED" if duration is not None else RUN_MISSING,
        },
        "ingest_job_id": song.get("ingest_job_id"),
        "filename_not_used_as_title": True,
    }


def _lyrics_extra(song: dict, executed: list[str]) -> dict:
    approved = song.get("approved_lyrics")
    if "lyrics_workflow" not in executed:
        return {}
    if not approved:
        return {
            "approval_state": "UNAVAILABLE",
            "approved_lyric_artifact_ref": None,
            "approved_lyric_revision": None,
            "canonical_lyrics_remain_authoritative": True,
        }
    dirname = song.get("pipeline_dirname") or "a2l_pipeline"
    return {
        "approval_state": approved.get("approval_status") or "APPROVED",
        "approved_lyric_artifact_ref": f"ingest/{song['ingest_job_id']}/{dirname}/approved_lyrics/approved_lyrics.json",
        "approved_lyric_txt_ref": f"ingest/{song['ingest_job_id']}/{dirname}/approved_lyrics/approved_lyrics.txt",
        "approved_lyric_revision": approved.get("revision"),
        "canonical_lyrics_remain_authoritative": True,
        "text_duplicated_in_record": False,
    }


def _lyrics_engineering(song: dict, executed: list[str], modules: dict) -> str:
    if "lyrics_workflow" not in executed:
        return ENGINEERING_NOT_RUN
    status = (modules.get("lyrics_workflow") or {}).get("status")
    if status == STATUS_UNAVAILABLE:
        return RUN_UNAVAILABLE
    return ENGINEERING_WIN


def _lyrics_authority(song: dict, executed: list[str]) -> str | None:
    if "lyrics_workflow" not in executed:
        return None
    if song.get("approved_lyrics"):
        return "HUMAN-APPROVED"
    return "AUTHORITATIVE INPUT"


def _key_mode_extra(fields: list[dict]) -> dict:
    extra = {
        "estimated_key": None,
        "estimated_mode": None,
        "confidence": {
            "value": None,
            "kind": "chroma profile correlation; not a calibrated probability",
            "calibrated_probability": False,
        },
        "alternates": [],
    }
    for field in fields:
        if field.get("id") == "key":
            extra["estimated_key"] = field.get("value")
        if field.get("id") == "mode":
            extra["estimated_mode"] = field.get("value")
        for item in field.get("evidence") or []:
            if item.get("label") == "score":
                extra["confidence"]["value"] = item.get("value")
            if item.get("label") == "alternates":
                extra["alternates"] = item.get("value") or []
    return extra


def _lyric_intel_extra(fields: list[dict], song: dict) -> dict:
    extra = {
        "approved_lyric_source_reference": None,
        "lexical_authority": "MEASURED",
        "interpretive_authority": "MACHINE-DERIVED",
        "artist_approved_interpretation": False,
    }
    approved = song.get("approved_lyrics")
    if approved:
        dirname = song.get("pipeline_dirname") or "a2l_pipeline"
        extra["approved_lyric_source_reference"] = (
            f"ingest/{song['ingest_job_id']}/{dirname}/approved_lyrics/approved_lyrics.json"
        )
    return extra


def _song_display_fields(song: dict) -> list[dict]:
    title = song.get("title") or {}
    artist = song.get("primary_artist") or {}
    duration = song.get("duration_seconds") or {}
    duration_value = duration.get("value")
    duration_text = f"{duration_value:.3f} s" if isinstance(duration_value, (int, float)) else None
    return [
        {
            "id": "title",
            "group": "song",
            "label": "Title",
            "value": title.get("value") or "Title not entered",
            "engine_id": "song_identity",
            "engine_label": "Song identity",
            "engine_technical": "Operator-entered metadata on the governed A2L song",
            "authority": title.get("authority") or RUN_MISSING,
            "status": STATUS_COMPLETE if title.get("value") else STATUS_UNAVAILABLE,
            "validation_state": "",
            "evidence": [],
            "note": "Filename is not used as the title.",
        },
        {
            "id": "artist",
            "group": "song",
            "label": "Artist",
            "value": artist.get("value") or "Artist not entered",
            "engine_id": "song_identity",
            "engine_label": "Song identity",
            "engine_technical": "Operator-entered metadata on the governed A2L song",
            "authority": artist.get("authority") or RUN_MISSING,
            "status": STATUS_COMPLETE if artist.get("value") else STATUS_UNAVAILABLE,
            "validation_state": "",
            "evidence": [],
            "note": "",
        },
        {
            "id": "duration",
            "group": "song",
            "label": "Duration",
            "value": duration_text or "unavailable",
            "engine_id": "song_identity",
            "engine_label": "Song identity",
            "engine_technical": "Measured from the ingested WAV",
            "authority": duration.get("authority") or RUN_MISSING,
            "status": STATUS_COMPLETE if duration_text else STATUS_UNAVAILABLE,
            "validation_state": "",
            "evidence": [],
            "note": "",
        },
    ]


def _not_run_field(engine_id: str, section_id: str) -> dict:
    group = {
        "lyrics": "lyrics",
        "rhythm_structure": "music",
        "key_mode": "music",
        "lyric_intelligence": "meaning",
    }.get(section_id, "provenance")
    spec = ENGINE_PROVENANCE.get(engine_id) or {}
    return {
        "id": f"{engine_id}_not_run",
        "group": group,
        "label": spec.get("capability") or engine_id,
        "value": "Not run",
        "engine_id": engine_id,
        "engine_label": spec.get("capability") or engine_id,
        "engine_technical": spec.get("method") or "",
        "authority": None,
        "status": STATUS_NOT_RUN,
        "validation_state": HUMAN_NOT_APPLICABLE,
        "evidence": [],
        "note": "Not run is not a failure.",
    }


def _record_provenance_field(record: dict) -> dict:
    return {
        "id": "governed_record",
        "group": "provenance",
        "label": "Governed Song Intelligence Record",
        "value": f"{RECORD_TYPE} revision {record.get('revision')}",
        "engine_id": "song_intelligence_record",
        "engine_label": "Song Intelligence Record",
        "engine_technical": f"schema {record.get('schema_version')}",
        "authority": AUTHORITY_OF_RECORD,
        "status": STATUS_COMPLETE,
        "validation_state": "",
        "evidence": [
            {"record_type": RECORD_TYPE, "revision": record.get("revision"), "ingest_job_id": record.get("ingest_job_id")}
        ],
        "note": "The record is governed current truth about what A2L knows. Contained analyzer values remain MACHINE-DERIVED unless otherwise classified.",
    }


def _audio_modules(section: dict) -> list[dict]:
    rows = []
    categories = section.get("categories") or {}
    labels = {
        "energy_intensity": "Energy / Intensity",
        "acoustic_electronic": "Acoustic / Electronic",
        "genre_style": "Genre / Style",
        "vocal_characteristics": "Vocal Characteristics",
        "instrumentation": "Instrumentation",
    }
    for category_id, engine_id in AUDIO_CATEGORY_ENGINES.items():
        cat = categories.get(category_id) or {}
        rows.append(
            {
                "id": engine_id if category_id not in {"energy_intensity", "acoustic_electronic", "vocal_characteristics"} else f"{engine_id}:{category_id}",
                "label": labels[category_id],
                "technical": (ENGINE_PROVENANCE.get(engine_id) or {}).get("method") or "",
                "status": _display_status(cat.get("run_state")),
                "message": cat.get("defect_disposition") if category_id == "instrumentation" else "",
                "result_origin": cat.get("result_origin"),
                "engineering_validation": cat.get("engineering_validation"),
            }
        )
    return rows


def _display_status(run_state: str | None) -> str:
    return {
        RUN_NOT_RUN: STATUS_NOT_RUN,
        RUN_AVAILABLE: STATUS_COMPLETE,
        RUN_PARTIAL: STATUS_PARTIAL,
        RUN_UNAVAILABLE: STATUS_UNAVAILABLE,
        RUN_FAILED: STATUS_FAILED,
        RUN_MISSING: STATUS_UNAVAILABLE,
    }.get(run_state or RUN_NOT_RUN, STATUS_NOT_RUN)


def _overall_display_status(record: dict) -> str:
    states = [
        (record.get("lyrics") or {}).get("run_state"),
        (record.get("rhythm_structure") or {}).get("run_state"),
        (record.get("key_mode") or {}).get("run_state"),
        (record.get("audio_intelligence") or {}).get("run_state"),
        (record.get("lyric_intelligence") or {}).get("run_state"),
    ]
    if any(item == RUN_PARTIAL for item in states):
        return STATUS_PARTIAL
    if any(item in {RUN_AVAILABLE} for item in states) and any(item in {RUN_NOT_RUN, RUN_UNAVAILABLE, RUN_FAILED} for item in states):
        return STATUS_PARTIAL
    if all(item == RUN_NOT_RUN for item in states):
        return STATUS_NOT_RUN
    return STATUS_COMPLETE
