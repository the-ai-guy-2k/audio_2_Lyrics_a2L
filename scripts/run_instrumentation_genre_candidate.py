"""ACI-A2L-SI-009 isolated instrumentation + genre tagging candidate.

Uses MIT Audio Spectrogram Transformer fine-tuned on AudioSet
(BSD-3-Clause). Does not continue CLAP prompt engineering. Does not
replace CLAP Energy / Acoustic / Vocal results. Does not modify the
master. Does not create a Song Intelligence Record.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI007_SCRIPT = ROOT / "scripts" / "run_audio_intelligence_candidate.py"
SI008_EVIDENCE = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-008-evidence"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-009-evidence"
CANDIDATE_DIR_NAME = "ast-instrumentation-genre"
ENGINE_NAME = "transformers ASTForAudioClassification"
CHECKPOINT = "MIT/ast-finetuned-audioset-10-10-0.4593"
CHECKPOINT_REVISION = "f826b80d28226b62986cc218e5cec390b1096902"
LICENSE_DECLARED = "bsd-3-clause"
SOFTWARE_LICENSE_DECLARED = (
    "Apache-2.0 (transformers, huggingface_hub); BSD-style (torch); ISC (librosa)"
)
ALLOWED_LICENSES = {
    "apache-2.0",
    "bsd-3-clause",
    "bsd-2-clause",
    "mit",
    "isc",
    "cc-by-4.0",
}
CACHE_ROOT = Path(os.environ.get("A2L_AST_CACHE", Path.home() / ".cache" / "a2l-ast"))
TARGET_SAMPLE_RATE = 16000
CHUNK_SECONDS = 10.24
HOP_SECONDS = 10.24
MIN_CHUNK_SECONDS = 1.0
SCORE_KIND = (
    "sigmoid_score is the mean AudioSet multi-label sigmoid over 10.24s chunks; "
    "it is a model-native ranking score, not a calibrated probability"
)
METHOD = (
    "in-memory 16 kHz mono resample of the locked master; AST log-mel spectrogram "
    "per 10.24s chunk; mean-pool sigmoid scores across chunks; native AudioSet 527 "
    "tags preserved; instrument and genre subsets filtered from native names; "
    "optional documented groups use max(member scores)"
)

# Native AudioSet names from MIT/ast-finetuned-audioset-10-10-0.4593 id2label.
# Not the SI-007 CLAP vocabulary. Generic parents stay in RAW only.
INSTRUMENT_LABELS = frozenset(
    {
        "Plucked string instrument",
        "Guitar",
        "Electric guitar",
        "Bass guitar",
        "Acoustic guitar",
        "Steel guitar, slide guitar",
        "Tapping (guitar technique)",
        "Strum",
        "Banjo",
        "Sitar",
        "Mandolin",
        "Zither",
        "Ukulele",
        "Keyboard (musical)",
        "Piano",
        "Electric piano",
        "Organ",
        "Electronic organ",
        "Hammond organ",
        "Synthesizer",
        "Sampler",
        "Harpsichord",
        "Percussion",
        "Drum kit",
        "Drum machine",
        "Drum",
        "Snare drum",
        "Rimshot",
        "Drum roll",
        "Bass drum",
        "Timpani",
        "Tabla",
        "Cymbal",
        "Hi-hat",
        "Wood block",
        "Tambourine",
        "Rattle (instrument)",
        "Maraca",
        "Gong",
        "Tubular bells",
        "Mallet percussion",
        "Marimba, xylophone",
        "Glockenspiel",
        "Vibraphone",
        "Steelpan",
        "Orchestra",
        "Brass instrument",
        "French horn",
        "Trumpet",
        "Trombone",
        "Bowed string instrument",
        "String section",
        "Violin, fiddle",
        "Pizzicato",
        "Cello",
        "Double bass",
        "Wind instrument, woodwind instrument",
        "Flute",
        "Saxophone",
        "Clarinet",
        "Harp",
        "Bell",
        "Harmonica",
        "Accordion",
        "Bagpipes",
        "Didgeridoo",
        "Theremin",
        "Scratching (performance technique)",
    }
)
GENRE_LABELS = frozenset(
    {
        "Pop music",
        "Hip hop music",
        "Rock music",
        "Heavy metal",
        "Punk rock",
        "Grunge",
        "Progressive rock",
        "Rock and roll",
        "Psychedelic rock",
        "Rhythm and blues",
        "Soul music",
        "Reggae",
        "Country",
        "Swing music",
        "Bluegrass",
        "Funk",
        "Folk music",
        "Middle Eastern music",
        "Jazz",
        "Disco",
        "Classical music",
        "Opera",
        "Electronic music",
        "House music",
        "Techno",
        "Dubstep",
        "Drum and bass",
        "Electronica",
        "Electronic dance music",
        "Ambient music",
        "Trance music",
        "Music of Latin America",
        "Salsa music",
        "Flamenco",
        "Blues",
        "Music for children",
        "New-age music",
        "Music of Africa",
        "Afrobeat",
        "Christian music",
        "Gospel music",
        "Music of Asia",
        "Carnatic music",
        "Music of Bollywood",
        "Ska",
        "Traditional music",
        "Independent music",
        "Dance music",
    }
)
INSTRUMENT_GROUPS = {
    "guitar_family": (
        "Guitar",
        "Electric guitar",
        "Acoustic guitar",
        "Bass guitar",
        "Steel guitar, slide guitar",
        "Tapping (guitar technique)",
        "Strum",
    ),
    "drums_percussion": (
        "Percussion",
        "Drum kit",
        "Drum machine",
        "Drum",
        "Snare drum",
        "Rimshot",
        "Drum roll",
        "Bass drum",
        "Cymbal",
        "Hi-hat",
        "Tambourine",
        "Wood block",
        "Rattle (instrument)",
        "Maraca",
        "Gong",
        "Timpani",
        "Tabla",
    ),
    "keyboard_piano_organ": (
        "Keyboard (musical)",
        "Piano",
        "Electric piano",
        "Organ",
        "Electronic organ",
        "Hammond organ",
        "Harpsichord",
    ),
    "synthesizer_electronic": ("Synthesizer", "Sampler", "Drum machine"),
    "strings_bowed": (
        "Bowed string instrument",
        "String section",
        "Violin, fiddle",
        "Pizzicato",
        "Cello",
        "Double bass",
        "Orchestra",
    ),
    "plucked_other": (
        "Plucked string instrument",
        "Banjo",
        "Sitar",
        "Mandolin",
        "Zither",
        "Ukulele",
        "Harp",
    ),
    "brass": ("Brass instrument", "French horn", "Trumpet", "Trombone"),
    "woodwind": (
        "Wind instrument, woodwind instrument",
        "Flute",
        "Saxophone",
        "Clarinet",
        "Harmonica",
    ),
}
GENERIC_PARENTS = frozenset(
    {
        "Music",
        "Musical instrument",
        "Song",
        "Background music",
        "Theme music",
        "Soundtrack music",
        "Jingle (music)",
        "Vocal music",
    }
)

# Engineering discrimination only. Not calibrated confidence.
STRONG_SCORE = 0.15
WEAK_SCORE = 0.05
MARGIN_WIN = 0.05
MARGIN_PARTIAL = 0.02
SPREAD_WIN = 0.10
TOP_RAW = 40


def load_si007():
    spec = importlib.util.spec_from_file_location("run_audio_intelligence_candidate", SI007_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_si007 = load_si007()


def normalize_license(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "-")


def assert_commercial_license(card_license: str | None) -> str:
    normalized = normalize_license(card_license)
    if normalized not in ALLOWED_LICENSES:
        raise SystemExit(
            f"LICENSE BLOCKER: checkpoint license {card_license!r} is not commercially acceptable"
        )
    return card_license or ""


def hub_repo_dir() -> Path:
    return CACHE_ROOT / "huggingface" / "hub" / f"models--{CHECKPOINT.replace('/', '--')}"


def snapshot_dir() -> Path:
    return hub_repo_dir() / "snapshots" / CHECKPOINT_REVISION


def license_from_local_readme() -> str | None:
    readme = snapshot_dir() / "README.md"
    if not readme.is_file():
        return None
    match = re.search(r"(?im)^license:\s*(\S+)", readme.read_text(encoding="utf-8"))
    if not match:
        return None
    return match.group(1)


def load_checkpoint_license() -> str:
    local = license_from_local_readme()
    if local:
        return assert_commercial_license(local)
    from huggingface_hub import model_info

    info = model_info(CHECKPOINT, revision=CHECKPOINT_REVISION)
    card = info.cardData or {}
    license_value = card.get("license") or getattr(info, "license", None)
    return assert_commercial_license(str(license_value) if license_value else None)


def local_weight_files() -> list[Path]:
    snap = snapshot_dir()
    return [path for path in (snap / "model.safetensors", snap / "pytorch_model.bin") if path.is_file()]


def ensure_local_checkpoint() -> dict:
    weights = local_weight_files()
    bytes_found = sum(path.stat().st_size for path in weights)
    local = bool(weights) and (snapshot_dir() / "config.json").is_file()
    return {
        "snapshot_dir": str(snapshot_dir()),
        "weight_files": [path.name for path in weights],
        "weight_bytes": bytes_found,
        "local_files_only": local,
        "action": "snapshot_complete" if local else "download_required",
    }


def isolate_model_cache() -> dict:
    hf_home = CACHE_ROOT / "huggingface"
    torch_home = CACHE_ROOT / "torch"
    hf_home.mkdir(parents=True, exist_ok=True)
    torch_home.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["TORCH_HOME"] = str(torch_home)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    # Inherited CLAP-session offline flags would block the first AST weight fetch.
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    return {
        "cache_root": str(CACHE_ROOT),
        "hf_home": str(hf_home),
        "torch_home": str(torch_home),
        "bytes_before": _si007.dir_size_bytes(CACHE_ROOT),
    }


def protected_roots(sha: str) -> list[Path]:
    return list(_si007.protected_roots(sha)) + [
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-007-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-008-evidence",
    ]


def assert_isolated_output(path: Path, sha: str) -> None:
    resolved = path.resolve()
    for root in protected_roots(sha):
        if not root.exists():
            continue
        protected = root.resolve()
        if resolved == protected or protected in resolved.parents:
            raise SystemExit(f"Refusing to write into protected artifact path: {resolved}")
    ingest = (ROOT / "artifacts" / "ingest").resolve()
    if ingest in resolved.parents or resolved == ingest:
        raise SystemExit(f"Refusing to write into ingest store: {resolved}")


def snapshot_protected(sha: str) -> dict:
    record = {}
    for root in protected_roots(sha):
        if not root.exists():
            record[str(root)] = {"exists": False, "files": {}}
            continue
        files = {}
        if root.is_file():
            files[str(root)] = _si007.sha256_file(root)
        else:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    files[str(path)] = _si007.sha256_file(path)
        record[str(root)] = {"exists": True, "files": files}
    return record


def rank_scores(items: list[dict], score_key: str = "sigmoid_score") -> list[dict]:
    ranked = sorted(items, key=lambda row: row[score_key], reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["score"] = row[score_key]
        row["score_kind"] = "sigmoid_score"
    return ranked


def separation_metrics(ranked: list[dict]) -> dict:
    if not ranked:
        return {"top_margin": None, "spread": None, "top1": None, "top2": None}
    scores = [row["sigmoid_score"] for row in ranked]
    top1 = scores[0]
    top2 = scores[1] if len(scores) > 1 else None
    strong = [row["label"] for row in ranked if row["sigmoid_score"] >= STRONG_SCORE]
    weak_count = sum(1 for value in scores if value < WEAK_SCORE)
    return {
        "top1": ranked[0]["label"],
        "top1_sigmoid": top1,
        "top2": ranked[1]["label"] if len(ranked) > 1 else None,
        "top2_sigmoid": top2,
        "top_margin": None if top2 is None else top1 - top2,
        "spread": max(scores) - min(scores),
        "max_sigmoid": max(scores),
        "min_sigmoid": min(scores),
        "strong_count": len(strong),
        "strong_labels": strong,
        "weak_count": weak_count,
        "label_count": len(ranked),
    }


def assess_category(separation: dict) -> dict:
    margin = separation.get("top_margin")
    spread = separation.get("spread") or 0.0
    strong_count = int(separation.get("strong_count") or 0)
    weak_count = int(separation.get("weak_count") or 0)
    label_count = int(separation.get("label_count") or 0)
    if margin is None:
        return {
            "category_result": "NO WIN",
            "assessment": "NO SCORES",
            "top_margin": None,
            "spread": spread,
            "strong_count": strong_count,
        }
    cluster = strong_count >= 2 and weak_count >= max(3, label_count // 2)
    useful = margin >= MARGIN_WIN or (strong_count >= 1 and spread >= SPREAD_WIN) or cluster
    if useful:
        result = "WIN"
        assessment = "USEFUL MULTI-LABEL" if cluster or strong_count >= 2 else "USEFUL"
    elif margin >= MARGIN_PARTIAL or strong_count >= 1:
        result = "PARTIAL"
        assessment = "WEAK BUT PRESENT"
    else:
        result = "NO WIN"
        assessment = "STILL WEAK"
    return {
        "category_result": result,
        "assessment": assessment,
        "top_margin": margin,
        "spread": spread,
        "strong_count": strong_count,
        "weak_count": weak_count,
        "thresholds": {
            "strong_score": STRONG_SCORE,
            "weak_score": WEAK_SCORE,
            "margin_win": MARGIN_WIN,
            "margin_partial": MARGIN_PARTIAL,
            "spread_win": SPREAD_WIN,
            "score_kind": SCORE_KIND,
        },
    }


def engine3_result(instrumentation: str, genre_style: str) -> str:
    if instrumentation == "WIN" and genre_style == "WIN":
        return "ENGINEERING WIN"
    return "PARTIAL PASS"


def group_scores(ranked: list[dict]) -> list[dict]:
    by_label = {row["label"]: row["sigmoid_score"] for row in ranked}
    grouped = []
    for name, members in INSTRUMENT_GROUPS.items():
        present = [member for member in members if member in by_label]
        if not present:
            continue
        grouped.append(
            {
                "group": name,
                "label": name,
                "mapping": "max(member sigmoid_score)",
                "members_present": present,
                "sigmoid_score": max(by_label[member] for member in present),
                "member_scores": {member: by_label[member] for member in present},
            }
        )
    return rank_scores(grouped)


def filter_subset(all_ranked: list[dict], labels: frozenset[str]) -> list[dict]:
    subset = [dict(row) for row in all_ranked if row["label"] in labels]
    return rank_scores(subset)


def clap_comparison_from_si008() -> dict:
    run_path = SI008_EVIDENCE / "classification_resolution_run.json"
    raw_path = SI008_EVIDENCE / "classification_resolution_raw.json"
    if not run_path.is_file() or not raw_path.is_file():
        return {"available": False, "reason": "SI-008 evidence missing"}
    run = json.loads(run_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    categories = ((raw.get("resolution") or {}).get("categories")) or {}
    extracted = {}
    for name in ("instrumentation", "genre_style"):
        block = categories.get(name) or {}
        resolution = block.get("resolution") or {}
        ranked = resolution.get("ranked") or []
        assessment = block.get("assessment") or {}
        extracted[name] = {
            "clap_result": (run.get("category_results") or {}).get(name),
            "selected_method": block.get("selected_method"),
            "top1": ranked[0]["label"] if ranked else None,
            "top1_cosine": ranked[0].get("cosine_similarity") if ranked else None,
            "top2": ranked[1]["label"] if len(ranked) > 1 else None,
            "top_margin": assessment.get("top_margin"),
            "spread": assessment.get("spread"),
            "assessment": assessment.get("assessment"),
        }
    return {
        "available": True,
        "source": "preserved SI-008 evidence; CLAP was not rerun",
        "engine3_result": run.get("engine3_result"),
        "category_results": run.get("category_results"),
        "clap": extracted,
    }


def package_versions() -> dict:
    names = [
        "transformers",
        "torch",
        "librosa",
        "numpy",
        "scipy",
        "soundfile",
        "huggingface_hub",
        "safetensors",
    ]
    found = {}
    from importlib.metadata import PackageNotFoundError, version

    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def analyze_mix(path: Path) -> dict:
    cache = isolate_model_cache()
    import numpy as np
    import torch
    from transformers import ASTForAudioClassification, AutoFeatureExtractor
    import librosa

    recorded_license = load_checkpoint_license()
    checkpoint_state = ensure_local_checkpoint()
    download_required = not bool(checkpoint_state.get("local_files_only"))
    local_only = bool(checkpoint_state.get("local_files_only"))
    audio, sample_rate = librosa.load(str(path), sr=TARGET_SAMPLE_RATE, mono=True)
    ranges = _si007.chunk_ranges(
        len(audio),
        int(sample_rate),
        chunk_seconds=CHUNK_SECONDS,
        hop_seconds=HOP_SECONDS,
        min_seconds=MIN_CHUNK_SECONDS,
    )
    extractor = AutoFeatureExtractor.from_pretrained(
        CHECKPOINT, revision=CHECKPOINT_REVISION, local_files_only=local_only
    )
    model = ASTForAudioClassification.from_pretrained(
        CHECKPOINT, revision=CHECKPOINT_REVISION, local_files_only=local_only
    )
    model.to("cpu")
    model.eval()
    id2label = {int(key): value for key, value in model.config.id2label.items()}

    chunk_probs: list = []
    inference_started = time.perf_counter()
    with torch.no_grad():
        for start, end in ranges:
            chunk = np.asarray(audio[start:end], dtype=np.float32)
            inputs = extractor(chunk, sampling_rate=int(sample_rate), return_tensors="pt")
            inputs = {key: value.to("cpu") for key, value in inputs.items()}
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits)[0].detach().cpu()
            chunk_probs.append(probs)
            del inputs, logits
    inference_seconds = time.perf_counter() - inference_started
    checkpoint_after = ensure_local_checkpoint()
    checkpoint_state = {
        **checkpoint_state,
        "download_required": download_required,
        "weight_bytes_after": checkpoint_after.get("weight_bytes"),
        "weight_files_after": checkpoint_after.get("weight_files"),
        "local_files_only_after": checkpoint_after.get("local_files_only"),
    }
    stacked = torch.stack(chunk_probs)
    mean_probs = stacked.mean(dim=0).tolist()
    all_items = []
    for index, score in enumerate(mean_probs):
        label = id2label.get(index, str(index))
        all_items.append(
            {
                "index": index,
                "label": label,
                "display": label,
                "sigmoid_score": float(score),
            }
        )
    all_ranked = rank_scores(all_items)
    instrumentation = filter_subset(all_ranked, INSTRUMENT_LABELS)
    genre_style = filter_subset(all_ranked, GENRE_LABELS)
    inst_sep = separation_metrics(instrumentation)
    genre_sep = separation_metrics(genre_style)
    inst_assess = assess_category(inst_sep)
    genre_assess = assess_category(genre_sep)
    return {
        "license": recorded_license,
        "cache": cache,
        "checkpoint_state": checkpoint_state,
        "cache_bytes_after": _si007.dir_size_bytes(CACHE_ROOT),
        "checkpoint_snapshot_bytes": _si007.dir_size_bytes(hub_repo_dir()),
        "sample_rate_derived": int(sample_rate),
        "source_preprocessing": (
            "in-memory librosa load to 16 kHz mono float32 for AST; "
            "source WAV was not overwritten, remastered, or normalized on disk"
        ),
        "duration_seconds": float(len(audio) / sample_rate) if sample_rate else None,
        "chunk_count": len(chunk_probs),
        "chunk_seconds": CHUNK_SECONDS,
        "inference_seconds": inference_seconds,
        "id2label_count": len(id2label),
        "score_kind": SCORE_KIND,
        "raw_top": all_ranked[:TOP_RAW],
        "instrumentation": {
            "taxonomy": "native AudioSet instrument labels; SI-007 CLAP vocabulary was not forced",
            "ranked": instrumentation,
            "separation": inst_sep,
            "assessment": inst_assess,
            "groups": group_scores(instrumentation),
        },
        "genre_style": {
            "taxonomy": "native AudioSet genre/style labels; SI-007 CLAP vocabulary was not forced",
            "ranked": genre_style,
            "separation": genre_sep,
            "assessment": genre_assess,
        },
        "generic_parents": filter_subset(all_ranked, GENERIC_PARENTS),
        "category_results": {
            "instrumentation": inst_assess["category_result"],
            "genre_style": genre_assess["category_result"],
        },
        "engine3_result": engine3_result(
            inst_assess["category_result"], genre_assess["category_result"]
        ),
    }


def format_ranked(rows: list[dict], limit: int | None = None) -> list[str]:
    lines = []
    shown = rows if limit is None else rows[:limit]
    for row in shown:
        name = row.get("display") or row.get("label") or row.get("group")
        lines.append(f"{row['rank']}. {name:<36} sigmoid={row['sigmoid_score']:.4f}")
    return lines


def write_readable_txt(path: Path, result: dict, meta: dict) -> None:
    inst = result.get("instrumentation") or {}
    genre = result.get("genre_style") or {}
    lines = [
        "MACHINE-DERIVED INSTRUMENTATION + GENRE / STYLE",
        "ACI-A2L-SI-009",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "AST AudioSet tags are MACHINE-DERIVED sigmoid scores, not calibrated probabilities.",
        "CLAP Energy / Acoustic / Vocal results were not replaced.",
        "",
        f"engine: {meta.get('engine')}",
        f"checkpoint: {meta.get('checkpoint')}",
        f"revision: {meta.get('revision')}",
        f"model_license: {meta.get('license')}",
        f"software_license: {SOFTWARE_LICENSE_DECLARED}",
        "device: cpu",
        f"source_sha256: {meta.get('source_sha256')}",
        f"score_kind: {SCORE_KIND}",
        f"source_preprocessing: {result.get('source_preprocessing')}",
        "",
        "RAW TOP AUDIOSET TAGS",
        *format_ranked(result.get("raw_top") or []),
        "",
        "INSTRUMENTATION (native AudioSet subset)",
        *format_ranked(inst.get("ranked") or []),
        "",
        f"INSTRUMENTATION RESULT: {(inst.get('assessment') or {}).get('category_result')}",
        f"discrimination: {(inst.get('assessment') or {}).get('assessment')} "
        f"top_margin={(inst.get('separation') or {}).get('top_margin')} "
        f"spread={(inst.get('separation') or {}).get('spread')} "
        f"strong_count={(inst.get('separation') or {}).get('strong_count')}",
        "",
        "INSTRUMENT GROUPS (deterministic max of native members; raw preserved above)",
        *format_ranked(inst.get("groups") or []),
        "",
        "GENRE / STYLE (native AudioSet subset)",
        *format_ranked(genre.get("ranked") or []),
        "",
        f"GENRE / STYLE RESULT: {(genre.get('assessment') or {}).get('category_result')}",
        f"discrimination: {(genre.get('assessment') or {}).get('assessment')} "
        f"top_margin={(genre.get('separation') or {}).get('top_margin')} "
        f"spread={(genre.get('separation') or {}).get('spread')} "
        f"strong_count={(genre.get('separation') or {}).get('strong_count')}",
        "",
        f"ENGINE #3 RESULT: {result.get('engine3_result')}",
        "MUSICAL VALIDATION: PENDING JAY",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-009 instrumentation/genre candidate")
    parser.add_argument("--source", type=Path, default=_si007.LOCKED_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source
    if not source.is_file():
        print(f"FAIL: locked source not found: {source}")
        return 1

    before_sha = _si007.sha256_file(source)
    if before_sha != _si007.LOCKED_SHA256:
        print(f"FAIL: locked source SHA mismatch: {before_sha}")
        return 1

    ingest_source = (
        ROOT / "artifacts" / "ingest" / _si007.LOCKED_SHA256 / "authoritative_source" / "source.wav"
    )
    ingest_before = _si007.sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_before = snapshot_protected(_si007.LOCKED_SHA256)

    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / _si007.LOCKED_SHA256
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "instrumentation_genre_raw.json"
    txt_path = out_dir / "instrumentation_genre_readable.txt"
    run_path = out_dir / "instrumentation_genre_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, _si007.LOCKED_SHA256)

    versions = package_versions()
    hw = _si007.hardware_record()
    hw["notes"] = (
        "Instrumentation/genre AST is forced to CPU. GPU may exist but is not required. "
        "No cloud inference is used. Hugging Face Hub is weight distribution only."
    )
    errors: list[str] = []
    result: dict = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = _si007.MemorySampler()
    sampler.start()
    try:
        analyze_started = time.perf_counter()
        result = analyze_mix(source)
        analysis_seconds = time.perf_counter() - analyze_started
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = _si007.sha256_file(source)
    ingest_after = _si007.sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_after = snapshot_protected(_si007.LOCKED_SHA256)
    venv_dir = ROOT / ".venv-clap"
    comparison = clap_comparison_from_si008()

    raw_payload = {
        "candidate": "ACI-A2L-SI-009",
        "repair_attempt": "2 of 3",
        "authority": {
            "master_wav": "AUTHORITATIVE INPUT",
            "native_ast_tags": "MACHINE-DERIVED",
            "instrumentation": "MACHINE-DERIVED",
            "genre_style": "MACHINE-DERIVED",
            "grouped_tags": "MACHINE-DERIVED",
        },
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "clap_replaced": False,
        "clap_prompt_engineering_continued": False,
        "chords_estimated": False,
        "engine": ENGINE_NAME,
        "checkpoint": CHECKPOINT,
        "checkpoint_revision": CHECKPOINT_REVISION,
        "model_source": f"https://huggingface.co/{CHECKPOINT}/tree/{CHECKPOINT_REVISION}",
        "method": METHOD,
        "software_license": SOFTWARE_LICENSE_DECLARED,
        "model_license": result.get("license") or LICENSE_DECLARED,
        "license_evidence": {
            "huggingface_card": "license: bsd-3-clause",
            "original_ast_repo": "BSD 3-Clause License (Yuan Gong, 2021)",
            "audioset_dataset": "CC BY 4.0",
            "audioset_ontology": "CC BY-SA 4.0 (native class names emitted; ontology not adapted)",
            "not_inferred_from_transformers_license": True,
        },
        "score_kind": SCORE_KIND,
        "instrument_labels": sorted(INSTRUMENT_LABELS),
        "genre_labels": sorted(GENRE_LABELS),
        "instrument_groups": {key: list(value) for key, value in INSTRUMENT_GROUPS.items()},
        "gpu_required": False,
        "cloud_required": False,
        "device": "cpu",
        "sidecar": ".venv-clap (reused SI-007 CPU torch/transformers; AST added no new packages)",
        "source_path": str(source),
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "ingest_source_sha256_before": ingest_before,
        "ingest_source_sha256_after": ingest_after,
        "analysis_seconds": analysis_seconds,
        "package_versions": versions,
        "hardware": hw,
        "venv_bytes": _si007.dir_size_bytes(venv_dir) if venv_dir.exists() else None,
        "cache_bytes_after": result.get("cache_bytes_after"),
        "checkpoint_snapshot_bytes": result.get("checkpoint_snapshot_bytes"),
        "checkpoint_state": result.get("checkpoint_state"),
        "memory": memory,
        "errors": errors,
        "clap_comparison": comparison,
        "instrumentation_genre": {
            key: value
            for key, value in result.items()
            if key not in {"cache"}
        },
        "cache": result.get("cache"),
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        result,
        {
            "engine": ENGINE_NAME,
            "checkpoint": CHECKPOINT,
            "revision": CHECKPOINT_REVISION,
            "license": result.get("license") or LICENSE_DECLARED,
            "source_sha256": after_sha,
        },
    )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "instrumentation_genre_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "instrumentation_genre_readable.txt")

    inst = (result.get("instrumentation") or {}).get("ranked")
    genre = (result.get("genre_style") or {}).get("ranked")
    ok = not errors and bool(inst) and bool(genre)
    source_sha_unchanged = before_sha == after_sha == _si007.LOCKED_SHA256 and (
        ingest_before is None or ingest_before == ingest_after == _si007.LOCKED_SHA256
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_sha_unchanged,
        "protected_artifacts_unchanged": _si007.snapshots_match(protected_before, protected_after),
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "download_required": bool((result.get("checkpoint_state") or {}).get("download_required")),
        "analysis_seconds": analysis_seconds,
        "inference_seconds": result.get("inference_seconds"),
        "engine3_result": result.get("engine3_result"),
        "category_results": result.get("category_results"),
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "instrumentation_genre_run.json")
    print(json.dumps(run_payload, indent=2))
    print(f"INSTRUMENTATION / GENRE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_sha_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not _si007.snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if not ok:
        print("FAIL: incomplete instrumentation/genre output")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
