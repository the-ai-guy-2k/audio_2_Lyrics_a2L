"""Promoted Song Intelligence engine adapters for the product UI.

Calls existing candidate analyze functions. Does not retune thresholds,
repair instrumentation, or create a governed Song Intelligence Record.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

from a2l.pipeline import ROOT

STATUS_COMPLETE = "Complete"
STATUS_PARTIAL = "Partial"
STATUS_UNAVAILABLE = "Unavailable"
STATUS_FAILED = "Failed"

VENV_BY_ENGINE = {
    "rhythm_structure": ".venv-all-in-one",
    "key_mode": ".venv-key-mode",
    "clap_audio": ".venv-clap",
    "ast_genre": ".venv-clap",
    "panns_instrumentation": ".venv-clap",
}

ENGINE_CATALOG = {
    "lyrics_workflow": {
        "label": "Approved Lyrics",
        "technical": "Existing A2L lyric transcription and approval workflow",
        "produces": ("lyrics",),
    },
    "rhythm_structure": {
        "label": "Rhythm + Structure Analyzer",
        "technical": "All-In-One / Harmonix (all-in-one-infer, mix-as-stems)",
        "produces": ("music",),
    },
    "key_mode": {
        "label": "Key + Mode Analyzer",
        "technical": "librosa chroma_cqt + Krumhansl–Kessler / Krumhansl–Schmuckler",
        "produces": ("music",),
    },
    "clap_audio": {
        "label": "Audio Intelligence (CLAP)",
        "technical": "LAION CLAP (laion/larger_clap_music) with deterministic RMS/onset energy",
        "produces": ("sound",),
    },
    "ast_genre": {
        "label": "Genre / Style",
        "technical": "AST (MIT/ast-finetuned-audioset-10-10-0.4593)",
        "produces": ("sound",),
    },
    "panns_instrumentation": {
        "label": "Instrumentation",
        "technical": "PANNs Cnn14 (Cnn14_mAP=0.431.pth)",
        "produces": ("sound",),
    },
    "lyric_intelligence": {
        "label": "Lyric Intelligence",
        "technical": "Deterministic in-repo NLP on AUTHORITATIVE APPROVED LYRICS",
        "produces": ("meaning",),
    },
}

_SCRIPTS = {
    "all_in_one": "run_all_in_one_candidate.py",
    "key_mode": "run_key_mode_candidate.py",
    "clap": "run_audio_intelligence_candidate.py",
    "clap_resolution": "run_audio_classification_resolution.py",
    "ast": "run_instrumentation_genre_candidate.py",
    "panns": "run_instrument_presence_candidate.py",
    "lyric_nlp": "run_lyric_intelligence_candidate.py",
}


def load_script(key: str):
    filename = _SCRIPTS[key]
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(f"a2l_si_{key}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_runners(allow_venv: bool = True) -> dict:
    runners = {
        "lyrics_workflow": run_lyrics_workflow,
        "rhythm_structure": run_rhythm_structure,
        "key_mode": run_key_mode,
        "clap_audio": run_clap_audio,
        "ast_genre": run_ast_genre,
        "panns_instrumentation": run_panns_instrumentation,
        "lyric_intelligence": run_lyric_intelligence,
    }
    if not allow_venv:
        return runners
    return {
        engine_id: _with_venv(engine_id, runner) if engine_id in VENV_BY_ENGINE else runner
        for engine_id, runner in runners.items()
    }


def _venv_python(name: str) -> Path | None:
    path = ROOT / name / "Scripts" / "python.exe"
    if path.is_file():
        return path
    posix = ROOT / name / "bin" / "python"
    if posix.is_file():
        return posix
    return None


def _song_payload(song: dict) -> dict:
    payload = dict(song)
    for key in ("working_path", "source_path", "ui_dir", "job_dir"):
        if key in payload and payload[key] is not None:
            payload[key] = str(payload[key])
    return payload


def _run_in_venv(engine_id: str, song: dict) -> dict | None:
    python = _venv_python(VENV_BY_ENGINE[engine_id])
    if python is None:
        return None
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    env.setdefault("PYTHONIOENCODING", "utf-8")
    payload = json.dumps({"engine_id": engine_id, "song": _song_payload(song)})
    completed = subprocess.run(
        [str(python), "-m", "a2l.song_intelligence_worker"],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
        timeout=45 * 60,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _with_venv(engine_id: str, runner):
    def wrapped(song: dict) -> dict:
        result = runner(song)
        if result.get("status") != STATUS_UNAVAILABLE:
            return result
        venv_result = _run_in_venv(engine_id, song)
        return venv_result or result

    return wrapped


def run_lyrics_workflow(song: dict) -> dict:
    spec = ENGINE_CATALOG["lyrics_workflow"]
    approved = song.get("approved_lyrics")
    if not approved:
        return {
            "status": STATUS_UNAVAILABLE,
            "message": "Unavailable — Approved Lyrics Required",
            "fields": [
                _field(
                    "approved_lyric_status",
                    "lyrics",
                    "Approved lyric status",
                    "Unavailable — Approved Lyrics Required",
                    engine_id="lyrics_workflow",
                    engine_label=spec["label"],
                    engine_technical=spec["technical"],
                    authority="AUTHORITATIVE INPUT",
                    status=STATUS_UNAVAILABLE,
                    validation_state="",
                    note="Lyric Intelligence and lyric display require approved lyrics. Unapproved transcription was not used.",
                )
            ],
        }
    return {
        "status": STATUS_COMPLETE,
        "message": "",
        "fields": [
            _field(
                "approved_lyric_status",
                "lyrics",
                "Approved lyric status",
                "APPROVED",
                engine_id="lyrics_workflow",
                engine_label=spec["label"],
                engine_technical=spec["technical"],
                authority="HUMAN-APPROVED",
                status=STATUS_COMPLETE,
                validation_state="",
            ),
            _field(
                "approved_lyrics",
                "lyrics",
                "Approved lyrics",
                approved.get("text") or "",
                engine_id="lyrics_workflow",
                engine_label=spec["label"],
                engine_technical=spec["technical"],
                authority=approved.get("authority") or "AUTHORITATIVE",
                status=STATUS_COMPLETE,
                validation_state="",
                evidence=[{"revision": approved.get("revision")}],
            ),
        ],
    }


def run_lyric_intelligence(song: dict) -> dict:
    spec = ENGINE_CATALOG["lyric_intelligence"]
    approved = song.get("approved_lyrics")
    if not approved:
        return {
            "status": STATUS_UNAVAILABLE,
            "message": "Unavailable — Approved Lyrics Required",
            "fields": [
                _field(
                    "lyric_intelligence",
                    "meaning",
                    "Lyric Intelligence",
                    "Unavailable — Approved Lyrics Required",
                    engine_id="lyric_intelligence",
                    engine_label=spec["label"],
                    engine_technical=spec["technical"],
                    authority="AUTHORITATIVE INPUT",
                    status=STATUS_UNAVAILABLE,
                    validation_state="",
                    note="Approved lyrics were not substituted with an unapproved transcription.",
                )
            ],
        }
    module = load_script("lyric_nlp")
    analysis = module.analyze_lyrics(approved["text"])
    themes = [item.get("phrase") for item in analysis.get("themes") or [] if item.get("phrase")]
    keywords = [item.get("keyword") for item in analysis.get("keywords") or [] if item.get("keyword")]
    emotion = ((analysis.get("emotional_character") or {}).get("label")) or "unavailable"
    subject = ((analysis.get("subject_matter") or {}).get("text")) or "unavailable"
    synopsis = ((analysis.get("synopsis") or {}).get("text")) or "unavailable"
    shared = dict(
        engine_id="lyric_intelligence",
        engine_label=spec["label"],
        engine_technical=spec["technical"],
        authority="MACHINE-DERIVED",
        status=STATUS_COMPLETE,
        validation_state="PENDING HUMAN VALIDATION",
        note="Interpretive outputs remain machine-derived. Semantic validation is pending Jay.",
    )
    return {
        "status": STATUS_COMPLETE,
        "message": "",
        "fields": [
            _field("themes", "meaning", "Themes / subject phrases", themes or ["unavailable"], **shared),
            _field("subject_matter", "meaning", "Subject matter", subject, **shared),
            _field("emotional_character", "meaning", "Emotional character", emotion, **shared),
            _field("keywords", "meaning", "Keywords", keywords or ["unavailable"], **shared),
            _field("synopsis", "meaning", "Synopsis", synopsis, **shared),
        ],
    }


def run_key_mode(song: dict) -> dict:
    spec = ENGINE_CATALOG["key_mode"]
    try:
        module = load_script("key_mode")
        estimate = module.analyze_mix(Path(song["working_path"]))
    except Exception as exc:
        return _failed("key_mode", spec, exc)
    key = estimate.get("key") or "unavailable"
    mode = estimate.get("mode") or "unavailable"
    evidence = [
        {"label": "score", "value": estimate.get("score")},
        {
            "label": "alternates",
            "value": [
                f"{item.get('key')} {item.get('mode')} ({item.get('score')})"
                for item in (estimate.get("alternates") or [])[:5]
            ],
        },
    ]
    shared = dict(
        engine_id="key_mode",
        engine_label=spec["label"],
        engine_technical=spec["technical"],
        authority="MACHINE-DERIVED",
        status=STATUS_COMPLETE,
        validation_state="PENDING HUMAN VALIDATION",
        evidence=evidence,
        note="Musical validation is pending Jay. Not an authoritative song fact.",
    )
    return {
        "status": STATUS_COMPLETE,
        "message": "",
        "fields": [
            _field("key", "music", "Key", key, **shared),
            _field("mode", "music", "Mode", mode, **shared),
        ],
    }


def run_rhythm_structure(song: dict) -> dict:
    spec = ENGINE_CATALOG["rhythm_structure"]
    try:
        module = load_script("all_in_one")
        summary = _analyze_rhythm(module, Path(song["working_path"]), Path(song["ui_dir"]))
    except Exception as exc:
        return _failed("rhythm_structure", spec, exc)
    bpm = summary.get("bpm")
    beats = summary.get("beats_count")
    downbeats = summary.get("downbeats_count")
    structure = summary.get("structure_display") or []
    shared = dict(
        engine_id="rhythm_structure",
        engine_label=spec["label"],
        engine_technical=spec["technical"],
        authority="MACHINE-DERIVED",
        status=STATUS_COMPLETE,
        validation_state="PENDING HUMAN VALIDATION",
        note="Source separation is not exposed. Mix-as-stems Harmonix path only.",
    )
    return {
        "status": STATUS_COMPLETE,
        "message": "",
        "fields": [
            _field(
                "bpm",
                "music",
                "BPM",
                bpm if bpm is not None else "unavailable",
                evidence=[{"beats": beats, "downbeats": downbeats}],
                **shared,
            ),
            _field(
                "rhythm_evidence",
                "music",
                "Beat / downbeat evidence",
                f"{beats} beats, {downbeats} downbeats" if beats is not None else "unavailable",
                **shared,
            ),
            _field(
                "structure",
                "music",
                "Song structure",
                structure or ["unavailable"],
                **shared,
            ),
        ],
    }


def _analyze_rhythm(module, source: Path, ui_dir: Path) -> dict:
    work = Path(ui_dir) / "rhythm_work"
    work.mkdir(parents=True, exist_ok=True)
    working_copy = work / "source_pcm32.wav"
    engine_out = work / "engine_out"
    engine_out.mkdir(parents=True, exist_ok=True)
    module.isolate_model_cache()
    module.prepare_analysis_wav(source, working_copy)
    from allin1_infer import analyze
    from allin1_infer.stems_input import StemsInput

    stems = StemsInput(
        bass=working_copy,
        drums=working_copy,
        other=working_copy,
        vocals=working_copy,
        identifier="a2l-si-product-mix-as-stems",
    )
    result = analyze(
        stems_input=stems,
        out_dir=engine_out,
        visualize=False,
        sonify=False,
        model=getattr(module, "DEFAULT_MODEL", "harmonix-all"),
        device="cpu",
        include_activations=False,
        include_embeddings=False,
        demix_dir=work / "demix",
        spec_dir=work / "spec",
        keep_byproducts=False,
        overwrite=True,
        multiprocess=False,
    )
    return module.summarize_result(result)


def run_clap_audio(song: dict) -> dict:
    spec = ENGINE_CATALOG["clap_audio"]
    try:
        clap = load_script("clap")
        resolution_mod = load_script("clap_resolution")
        import librosa

        audio, sample_rate = librosa.load(str(song["working_path"]), sr=clap.TARGET_SAMPLE_RATE, mono=True)
        energy = clap.measure_energy(audio, int(sample_rate))
        resolution = resolution_mod.analyze_resolution(Path(song["working_path"]))
    except Exception as exc:
        return _failed("clap_audio", spec, exc)
    measured = energy.get("authority_measured") or {}
    derived = energy.get("authority_machine_derived") or {}
    acoustic = ((resolution.get("categories") or {}).get("acoustic_electronic") or {}).get("control") or {}
    vocal = ((resolution.get("categories") or {}).get("vocal_character") or {}).get("resolution") or {}
    acoustic_top = _top_labels(acoustic.get("ranked") or [], "cosine_similarity")
    vocal_top = _top_labels(vocal.get("ranked") or [], "cosine_similarity")
    energy_label = derived.get("energy_label") or "unavailable"
    energy_note = derived.get("rule") or "Energy label is machine-derived from measured RMS."
    fields = [
        _field(
            "energy",
            "sound",
            "Energy / Intensity",
            energy_label,
            engine_id="clap_audio",
            engine_label=spec["label"],
            engine_technical=spec["technical"],
            authority="MACHINE-DERIVED",
            status=STATUS_COMPLETE,
            validation_state="PENDING HUMAN VALIDATION",
            evidence=[
                {"label": "rms_mean", "value": measured.get("rms_mean"), "authority": "MEASURED"},
                {"label": "rms_peak", "value": measured.get("rms_peak"), "authority": "MEASURED"},
                {"label": "onset_count", "value": measured.get("onset_count"), "authority": "MEASURED"},
            ],
            note=energy_note,
        ),
        _field(
            "acoustic_electronic",
            "sound",
            "Acoustic / Electronic",
            acoustic_top[0]["label"] if acoustic_top else "unavailable",
            engine_id="clap_audio",
            engine_label=spec["label"],
            engine_technical="CLAP CONTROL (SI-007/SI-008)",
            authority="MACHINE-DERIVED",
            status=STATUS_COMPLETE,
            validation_state="PENDING HUMAN VALIDATION",
            evidence=acoustic_top[:5],
            note="CLAP cosine ranking, not a calibrated probability.",
        ),
        _field(
            "vocal_character",
            "sound",
            "Vocal Characteristics",
            vocal_top[0]["label"] if vocal_top else "unavailable",
            engine_id="clap_audio",
            engine_label=spec["label"],
            engine_technical="CLAP ensemble (SI-008)",
            authority="MACHINE-DERIVED",
            status=STATUS_PARTIAL,
            validation_state="PENDING HUMAN VALIDATION",
            evidence=vocal_top[:5],
            note="Partial. Not an authoritative vocal fact. Scores are not calibrated confidence.",
        ),
    ]
    return {"status": STATUS_PARTIAL, "message": "Vocal characteristics remain partial.", "fields": fields}


def run_ast_genre(song: dict) -> dict:
    spec = ENGINE_CATALOG["ast_genre"]
    try:
        module = load_script("ast")
        result = module.analyze_mix(Path(song["working_path"]))
    except Exception as exc:
        return _failed("ast_genre", spec, exc)
    ranked = ((result.get("genre_style") or {}).get("ranked")) or []
    top = _top_labels(ranked, "sigmoid_score")
    return {
        "status": STATUS_COMPLETE,
        "message": "",
        "fields": [
            _field(
                "genre_style",
                "sound",
                "Genre / Style",
                top[0]["label"] if top else "unavailable",
                engine_id="ast_genre",
                engine_label=spec["label"],
                engine_technical=spec["technical"],
                authority="MACHINE-DERIVED",
                status=STATUS_COMPLETE,
                validation_state="PENDING HUMAN VALIDATION",
                evidence=top[:8],
                note="AST AudioSet sigmoid scores are ranking scores, not calibrated probabilities.",
            )
        ],
    }


def run_panns_instrumentation(song: dict) -> dict:
    spec = ENGINE_CATALOG["panns_instrumentation"]
    try:
        module = load_script("panns")
        result = module.analyze_mix(Path(song["working_path"]))
    except Exception as exc:
        return _failed("panns_instrumentation", spec, exc)
    ranked = ((result.get("instrumentation") or {}).get("ranked")) or result.get("instrumentation_ranked") or []
    if not ranked and isinstance(result.get("instrumentation"), list):
        ranked = result["instrumentation"]
    top = _top_labels(ranked, "clipwise_mean")
    assessment = ((result.get("instrumentation") or {}).get("assessment")) or {}
    category = assessment.get("category_result") or "PARTIAL"
    display = ", ".join(item["label"] for item in top[:5]) if top else "unavailable"
    return {
        "status": STATUS_PARTIAL,
        "message": "Instrumentation remains partial. Not an Engineering WIN.",
        "fields": [
            _field(
                "instrumentation",
                "sound",
                "Instrumentation",
                display,
                engine_id="panns_instrumentation",
                engine_label=spec["label"],
                engine_technical=spec["technical"],
                authority="MACHINE-DERIVED",
                status=STATUS_PARTIAL,
                validation_state="PENDING HUMAN VALIDATION",
                evidence=top[:8],
                note=(
                    "Partial. Low/weak evidence. Clipwise mean is the song-level score; "
                    "window max is not treated as a song-level WIN. "
                    f"Analyzer assessment: {category}."
                ),
            )
        ],
    }


def _field(
    field_id: str,
    group: str,
    label: str,
    value,
    *,
    engine_id: str,
    engine_label: str,
    engine_technical: str,
    authority: str,
    status: str,
    validation_state: str = "PENDING HUMAN VALIDATION",
    evidence=None,
    note: str | None = None,
) -> dict:
    from a2l.song_intelligence import _field as make_field

    return make_field(
        field_id,
        group,
        label,
        value,
        engine_id=engine_id,
        engine_label=engine_label,
        engine_technical=engine_technical,
        authority=authority,
        status=status,
        validation_state=validation_state,
        evidence=evidence,
        note=note,
    )


def _top_labels(ranked: list, score_key: str, limit: int = 8) -> list[dict]:
    rows = []
    for item in ranked[:limit]:
        label = item.get("display") or item.get("label") or item.get("group")
        if not label:
            continue
        score = item.get(score_key)
        if score is None:
            score = item.get("score")
        rows.append({"label": label, "score": score, "score_kind": score_key})
    return rows


def _failed(engine_id: str, spec: dict, exc: Exception) -> dict:
    message = str(exc)
    unavailable = isinstance(exc, (ImportError, ModuleNotFoundError)) or "No module named" in message
    status = STATUS_UNAVAILABLE if unavailable else STATUS_FAILED
    text = (
        "Unavailable in this environment."
        if unavailable
        else "That analysis engine failed. Other results were kept."
    )
    return {
        "status": status,
        "message": text,
        "fields": [
            _field(
                f"{engine_id}_error",
                "provenance",
                spec["label"],
                text,
                engine_id=engine_id,
                engine_label=spec["label"],
                engine_technical=spec["technical"],
                authority="MACHINE-DERIVED",
                status=status,
                validation_state="",
                note=type(exc).__name__,
            )
        ],
    }
