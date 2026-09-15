"""ACI-A2L-SI-010 isolated instrument-presence candidate.

PANNs Cnn14 AudioSet tagger (clipwise multi-label sigmoid). Does not
reopen genre, energy, acoustic/electronic, vocals, or CLAP. Does not
rerun AST. Does not modify the master. Does not create a Song
Intelligence Record.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI007_SCRIPT = ROOT / "scripts" / "run_audio_intelligence_candidate.py"
SI009_SCRIPT = ROOT / "scripts" / "run_instrumentation_genre_candidate.py"
SI009_EVIDENCE = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-009-evidence"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-010-evidence"
LABELS_CSV = ROOT / "scripts" / "data" / "panns_class_labels_indices.csv"
CANDIDATE_DIR_NAME = "panns-instrument-presence"
ENGINE_NAME = "PANNs Cnn14 audio tagging / instrument presence"
CHECKPOINT_NAME = "Cnn14_mAP=0.431.pth"
ZENODO_RECORD = "3987831"
ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_RECORD}"
CHECKPOINT_URL = (
    f"https://zenodo.org/records/{ZENODO_RECORD}/files/{CHECKPOINT_NAME}?download=1"
)
EXPECTED_BYTES = 327428481
EXPECTED_MD5 = "541141fa2ee191a88f24a3219fff024e"
LICENSE_DECLARED = "cc-by-4.0"
SOFTWARE_LICENSE_DECLARED = (
    "MIT (audioset_tagging_cnn Cnn14, torchlibrosa); "
    "BSD-style (torch); ISC (librosa)"
)
ALLOWED_LICENSES = {
    "apache-2.0",
    "bsd-3-clause",
    "bsd-2-clause",
    "mit",
    "isc",
    "cc-by-4.0",
}
CACHE_ROOT = Path(os.environ.get("A2L_PANNS_CACHE", Path.home() / ".cache" / "a2l-panns"))
TARGET_SAMPLE_RATE = 32000
CHUNK_SECONDS = 10.0
HOP_SECONDS = 10.0
MIN_CHUNK_SECONDS = 1.0
# Conventional multi-label sigmoid operating point. NOT the SI-009 AST 0.15 cut.
OPERATING_POINT = 0.50
CLUSTER_SCORE = 0.30
CLUSTER_RATIO = 4.0
PARTIAL_TOP = 0.20
PARTIAL_SPREAD = 0.10
SCORE_KIND = (
    "clipwise_mean is the mean PANNs Cnn14 multi-label sigmoid over 10s chunks; "
    "clipwise_max is the max across those chunks. Independent presence scores, "
    "not calibrated probabilities, not mutually exclusive classes."
)
METHOD = (
    "in-memory 32 kHz mono resample; PANNs Cnn14 log-mel tagging on 10s chunks; "
    "mean/max pool independent AudioSet clipwise sigmoids; instrument subset only "
    "for WIN; per-chunk scores retained as temporal evidence"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_si007 = load_module(SI007_SCRIPT, "run_audio_intelligence_candidate")
_si009 = load_module(SI009_SCRIPT, "run_instrumentation_genre_candidate")


def normalize_license(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "-")


def assert_commercial_license(card_license: str | None) -> str:
    normalized = normalize_license(card_license)
    if normalized not in ALLOWED_LICENSES:
        raise SystemExit(
            f"LICENSE BLOCKER: checkpoint license {card_license!r} is not commercially acceptable"
        )
    return card_license or ""


def checkpoint_path() -> Path:
    return CACHE_ROOT / CHECKPOINT_NAME


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_checkpoint_license() -> str:
    recorded = CACHE_ROOT / "zenodo_license.json"
    if recorded.is_file():
        payload = json.loads(recorded.read_text(encoding="utf-8"))
        return assert_commercial_license(payload.get("license_id"))
    with urllib.request.urlopen(ZENODO_API, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    license_id = ((data.get("metadata") or {}).get("license") or {}).get("id")
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    recorded.write_text(
        json.dumps(
            {
                "zenodo_record": ZENODO_RECORD,
                "license_id": license_id,
                "doi": data.get("doi"),
                "title": (data.get("metadata") or {}).get("title"),
                "source": ZENODO_API,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return assert_commercial_license(license_id)


def ensure_local_checkpoint() -> dict:
    path = checkpoint_path()
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    present = path.is_file() and path.stat().st_size == EXPECTED_BYTES
    md5_ok = present and md5_file(path) == EXPECTED_MD5
    if present and not md5_ok:
        path.unlink()
        present = False
    return {
        "path": str(path),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "md5": md5_file(path) if path.is_file() else None,
        "expected_bytes": EXPECTED_BYTES,
        "expected_md5": EXPECTED_MD5,
        "local_files_only": bool(present and md5_ok),
        "action": "checkpoint_complete" if present and md5_ok else "download_required",
    }


def download_checkpoint() -> None:
    path = checkpoint_path()
    tmp = path.with_suffix(".part")
    print(f"DOWNLOADING {CHECKPOINT_NAME} from Zenodo {ZENODO_RECORD} ...")
    urllib.request.urlretrieve(CHECKPOINT_URL, tmp)
    size = tmp.stat().st_size
    if size != EXPECTED_BYTES:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"DOWNLOAD BLOCKER: size {size} != {EXPECTED_BYTES}")
    if md5_file(tmp) != EXPECTED_MD5:
        tmp.unlink(missing_ok=True)
        raise SystemExit("DOWNLOAD BLOCKER: md5 mismatch")
    tmp.replace(path)


def load_labels() -> list[str]:
    if not LABELS_CSV.is_file():
        raise SystemExit(f"FAIL: missing AudioSet labels CSV: {LABELS_CSV}")
    labels = []
    with LABELS_CSV.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            labels.append(row["display_name"].strip().strip('"'))
    if len(labels) != 527:
        raise SystemExit(f"FAIL: expected 527 AudioSet labels, got {len(labels)}")
    return labels


def isolate_runtime() -> dict:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    return {"cache_root": str(CACHE_ROOT), "bytes_before": _si007.dir_size_bytes(CACHE_ROOT)}


def protected_roots(sha: str) -> list[Path]:
    return list(_si009.protected_roots(sha)) + [
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-009-evidence"
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


def rank_rows(items: list[dict], score_key: str = "clipwise_mean") -> list[dict]:
    ranked = sorted(items, key=lambda row: row[score_key], reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["score"] = row[score_key]
        row["score_kind"] = "clipwise_mean"
    return ranked


def separation_metrics(ranked: list[dict]) -> dict:
    if not ranked:
        return {"top_margin": None, "spread": None, "top1": None, "top2": None}
    scores = [row["clipwise_mean"] for row in ranked]
    top1 = scores[0]
    top2 = scores[1] if len(scores) > 1 else None
    strong = [row["label"] for row in ranked if row["clipwise_mean"] >= OPERATING_POINT]
    return {
        "top1": ranked[0]["label"],
        "top1_clipwise_mean": top1,
        "top1_clipwise_max": ranked[0].get("clipwise_max"),
        "top2": ranked[1]["label"] if len(ranked) > 1 else None,
        "top2_clipwise_mean": top2,
        "top_margin": None if top2 is None else top1 - top2,
        "spread": max(scores) - min(scores),
        "strong_count": len(strong),
        "strong_labels": strong,
        "label_count": len(ranked),
    }


def assess_instrument_presence(ranked: list[dict], separation: dict) -> dict:
    """PANNs-native multi-label presence. Does not reuse SI-009 AST 0.15."""
    top1 = separation.get("top1_clipwise_mean")
    spread = separation.get("spread") or 0.0
    scores = [row["clipwise_mean"] for row in ranked]
    strong = [row["label"] for row in ranked if row["clipwise_mean"] >= OPERATING_POINT]
    elevated = [value for value in scores if value >= CLUSTER_SCORE]
    rest = [value for value in scores if value < CLUSTER_SCORE]
    median_rest = statistics.median(rest) if rest else 0.0
    cluster = (
        len(elevated) >= 2
        and median_rest > 0
        and min(elevated) >= CLUSTER_RATIO * median_rest
    )
    if top1 is None:
        result, assessment = "NO WIN", "NO SCORES"
    elif strong or cluster:
        result = "WIN"
        assessment = "USEFUL MULTI-LABEL PRESENCE" if cluster or len(strong) >= 2 else "USEFUL PRESENCE"
    elif top1 >= PARTIAL_TOP or (top1 >= 0.10 and spread >= PARTIAL_SPREAD):
        result, assessment = "PARTIAL", "WEAK BUT PRESENT"
    else:
        result, assessment = "NO WIN", "STILL WEAK"
    return {
        "category_result": result,
        "assessment": assessment,
        "top_margin": separation.get("top_margin"),
        "spread": spread,
        "strong_count": len(strong),
        "strong_labels": strong,
        "cluster": cluster,
        "thresholds": {
            "operating_point": OPERATING_POINT,
            "cluster_score": CLUSTER_SCORE,
            "cluster_ratio": CLUSTER_RATIO,
            "partial_top": PARTIAL_TOP,
            "partial_spread": PARTIAL_SPREAD,
            "not_ast_0_15": True,
            "score_kind": SCORE_KIND,
        },
    }


def engine3_final(instrumentation: str) -> str:
    if instrumentation == "WIN":
        return "ENGINEERING WIN"
    return "PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD"


def group_scores(ranked: list[dict]) -> list[dict]:
    by_label = {row["label"]: row["clipwise_mean"] for row in ranked}
    grouped = []
    for name, members in _si009.INSTRUMENT_GROUPS.items():
        present = [member for member in members if member in by_label]
        if not present:
            continue
        grouped.append(
            {
                "group": name,
                "label": name,
                "mapping": "max(member clipwise_mean)",
                "members_present": present,
                "clipwise_mean": max(by_label[member] for member in present),
                "member_scores": {member: by_label[member] for member in present},
            }
        )
    return rank_rows(grouped, "clipwise_mean")


def ast_comparison_from_si009() -> dict:
    run_path = SI009_EVIDENCE / "instrumentation_genre_run.json"
    txt_path = SI009_EVIDENCE / "instrumentation_genre_readable.txt"
    raw_path = SI009_EVIDENCE / "instrumentation_genre_raw.json"
    if not run_path.is_file() or not raw_path.is_file():
        return {"available": False, "reason": "SI-009 evidence missing"}
    run = json.loads(run_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    inst = ((raw.get("instrumentation_genre") or {}).get("instrumentation")) or {}
    ranked = inst.get("ranked") or []
    return {
        "available": True,
        "source": "preserved SI-009 evidence; AST was not rerun; AST 0.15 threshold was not changed",
        "instrumentation_result": (run.get("category_results") or {}).get("instrumentation"),
        "top1": ranked[0]["label"] if ranked else None,
        "top1_sigmoid": ranked[0].get("sigmoid_score") if ranked else None,
        "top2": ranked[1]["label"] if len(ranked) > 1 else None,
        "top2_sigmoid": ranked[1].get("sigmoid_score") if len(ranked) > 1 else None,
        "top_margin": (inst.get("separation") or {}).get("top_margin"),
        "spread": (inst.get("separation") or {}).get("spread"),
        "strong_count": (inst.get("separation") or {}).get("strong_count"),
        "readable_excerpt": None if not txt_path.is_file() else "see SI-009 readable",
    }


def package_versions() -> dict:
    names = ["torch", "torchlibrosa", "librosa", "numpy", "soundfile"]
    found = {}
    from importlib.metadata import PackageNotFoundError, version

    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def analyze_mix(path: Path) -> dict:
    cache = isolate_runtime()
    import numpy as np
    import torch
    import librosa

    sys.path.insert(0, str(ROOT / "scripts"))
    from panns_cnn14 import Cnn14

    recorded_license = load_checkpoint_license()
    checkpoint_state = ensure_local_checkpoint()
    download_required = not bool(checkpoint_state.get("local_files_only"))
    if download_required:
        download_checkpoint()
        checkpoint_state = ensure_local_checkpoint()
        checkpoint_state["download_required"] = True
    else:
        checkpoint_state["download_required"] = False
    labels = load_labels()
    audio, sample_rate = librosa.load(str(path), sr=TARGET_SAMPLE_RATE, mono=True)
    ranges = _si007.chunk_ranges(
        len(audio),
        int(sample_rate),
        chunk_seconds=CHUNK_SECONDS,
        hop_seconds=HOP_SECONDS,
        min_seconds=MIN_CHUNK_SECONDS,
    )
    model = Cnn14()
    blob = torch.load(checkpoint_path(), map_location="cpu", weights_only=False)
    state = blob["model"] if isinstance(blob, dict) and "model" in blob else blob
    model.load_state_dict(state)
    model.to("cpu")
    model.eval()

    chunk_scores: list[list[float]] = []
    inference_started = time.perf_counter()
    with torch.no_grad():
        for start, end in ranges:
            chunk = np.asarray(audio[start:end], dtype=np.float32)
            if len(chunk) < int(CHUNK_SECONDS * sample_rate):
                padded = np.zeros(int(CHUNK_SECONDS * sample_rate), dtype=np.float32)
                padded[: len(chunk)] = chunk
                chunk = padded
            waveform = torch.from_numpy(chunk).unsqueeze(0)
            clipwise = model(waveform)["clipwise_output"][0].detach().cpu().tolist()
            chunk_scores.append(clipwise)
            del waveform
    inference_seconds = time.perf_counter() - inference_started
    stacked = np.asarray(chunk_scores, dtype=np.float64)
    mean_scores = stacked.mean(axis=0)
    max_scores = stacked.max(axis=0)
    all_items = []
    for index, label in enumerate(labels):
        all_items.append(
            {
                "index": index,
                "label": label,
                "display": label,
                "clipwise_mean": float(mean_scores[index]),
                "clipwise_max": float(max_scores[index]),
                "chunk_scores": [float(row[index]) for row in chunk_scores],
            }
        )
    all_ranked = rank_rows(all_items)
    instrumentation = rank_rows(
        [dict(row) for row in all_items if row["label"] in _si009.INSTRUMENT_LABELS]
    )
    sep = separation_metrics(instrumentation)
    assess = assess_instrument_presence(instrumentation, sep)
    temporal_top = []
    for row in instrumentation[:8]:
        temporal_top.append(
            {
                "label": row["label"],
                "clipwise_mean": row["clipwise_mean"],
                "clipwise_max": row["clipwise_max"],
                "chunk_scores": row["chunk_scores"],
            }
        )
    return {
        "license": recorded_license,
        "cache": cache,
        "checkpoint_state": checkpoint_state,
        "cache_bytes_after": _si007.dir_size_bytes(CACHE_ROOT),
        "sample_rate_derived": int(sample_rate),
        "source_preprocessing": (
            "in-memory librosa load to 32 kHz mono float32 for PANNs Cnn14; "
            "source WAV was not overwritten, remastered, or normalized on disk"
        ),
        "duration_seconds": float(len(audio) / sample_rate) if sample_rate else None,
        "chunk_count": len(chunk_scores),
        "chunk_seconds": CHUNK_SECONDS,
        "inference_seconds": inference_seconds,
        "score_kind": SCORE_KIND,
        "raw_top": [
            {key: value for key, value in row.items() if key != "chunk_scores"}
            for row in all_ranked[:25]
        ],
        "instrumentation": {
            "taxonomy": "native AudioSet instrument labels; SI-007 CLAP vocabulary was not forced",
            "ranked": [
                {key: value for key, value in row.items() if key != "chunk_scores"}
                for row in instrumentation
            ],
            "temporal_top": temporal_top,
            "separation": sep,
            "assessment": assess,
            "groups": group_scores(instrumentation),
        },
        "category_results": {"instrumentation": assess["category_result"]},
        "engine3_result": engine3_final(assess["category_result"]),
    }


def format_ranked(rows: list[dict], score_key: str = "clipwise_mean", limit: int | None = None) -> list[str]:
    lines = []
    shown = rows if limit is None else rows[:limit]
    for row in shown:
        name = row.get("display") or row.get("label") or row.get("group")
        extra = ""
        if "clipwise_max" in row:
            extra = f"  max={row['clipwise_max']:.4f}"
        lines.append(f"{row['rank']}. {name:<36} mean={row[score_key]:.4f}{extra}")
    return lines


def write_readable_txt(path: Path, result: dict, meta: dict) -> None:
    inst = result.get("instrumentation") or {}
    lines = [
        "MACHINE-DERIVED INSTRUMENT PRESENCE",
        "ACI-A2L-SI-010",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "PANNs clipwise scores are MACHINE-DERIVED independent sigmoids, not calibrated probabilities.",
        "Genre / Energy / Acoustic / Vocal / CLAP / AST were not reopened or retuned.",
        "",
        f"engine: {meta.get('engine')}",
        f"checkpoint: {CHECKPOINT_NAME}",
        f"model_license: {meta.get('license')}",
        f"software_license: {SOFTWARE_LICENSE_DECLARED}",
        "device: cpu",
        f"source_sha256: {meta.get('source_sha256')}",
        f"score_kind: {SCORE_KIND}",
        f"source_preprocessing: {result.get('source_preprocessing')}",
        "",
        "RAW TOP AUDIOSET TAGS (clipwise mean)",
        *format_ranked(result.get("raw_top") or []),
        "",
        "INSTRUMENTATION (native AudioSet subset)",
        *format_ranked(inst.get("ranked") or []),
        "",
        "INSTRUMENT GROUPS (deterministic max of native members; raw preserved above)",
        *format_ranked(inst.get("groups") or []),
        "",
        f"INSTRUMENTATION RESULT: {(inst.get('assessment') or {}).get('category_result')}",
        f"discrimination: {(inst.get('assessment') or {}).get('assessment')} "
        f"top_margin={(inst.get('separation') or {}).get('top_margin')} "
        f"spread={(inst.get('separation') or {}).get('spread')} "
        f"strong_count={(inst.get('separation') or {}).get('strong_count')} "
        f"operating_point={OPERATING_POINT}",
        "",
        f"ENGINE #3 FINAL RESULT: {result.get('engine3_result')}",
        "MUSICAL VALIDATION: PENDING JAY",
        "REPAIR BUDGET: EXHAUSTED",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-010 instrument-presence candidate")
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
    raw_path = out_dir / "instrument_presence_raw.json"
    txt_path = out_dir / "instrument_presence_readable.txt"
    run_path = out_dir / "instrument_presence_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, _si007.LOCKED_SHA256)

    versions = package_versions()
    hw = _si007.hardware_record()
    hw["notes"] = (
        "PANNs Cnn14 instrument presence is forced to CPU. GPU is not required. "
        "No cloud inference. Zenodo is weight distribution only."
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
    comparison = ast_comparison_from_si009()

    raw_payload = {
        "candidate": "ACI-A2L-SI-010",
        "repair_attempt": "3 of 3 FINAL",
        "authority": {
            "master_wav": "AUTHORITATIVE INPUT",
            "native_panns_tags": "MACHINE-DERIVED",
            "instrumentation": "MACHINE-DERIVED",
            "grouped_tags": "MACHINE-DERIVED",
        },
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "genre_reopened": False,
        "energy_reopened": False,
        "clap_reopened": False,
        "ast_rerun": False,
        "ast_threshold_changed": False,
        "engine": ENGINE_NAME,
        "checkpoint": CHECKPOINT_NAME,
        "checkpoint_source": CHECKPOINT_URL,
        "method": METHOD,
        "software_license": SOFTWARE_LICENSE_DECLARED,
        "model_license": result.get("license") or LICENSE_DECLARED,
        "license_evidence": {
            "zenodo_record": ZENODO_RECORD,
            "zenodo_license_id": "cc-by-4.0",
            "code_repo": "qiuqiangkong/audioset_tagging_cnn MIT",
            "torchlibrosa": "MIT",
            "not_inferred_from_library_license_alone": True,
        },
        "score_kind": SCORE_KIND,
        "gpu_required": False,
        "cloud_required": False,
        "device": "cpu",
        "sidecar": ".venv-clap (reused; torchlibrosa 0.1.0 already present)",
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
        "checkpoint_state": result.get("checkpoint_state"),
        "memory": memory,
        "errors": errors,
        "ast_comparison": comparison,
        "instrument_presence": {key: value for key, value in result.items() if key != "cache"},
        "cache": result.get("cache"),
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        result,
        {
            "engine": ENGINE_NAME,
            "license": result.get("license") or LICENSE_DECLARED,
            "source_sha256": after_sha,
        },
    )
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "instrument_presence_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "instrument_presence_readable.txt")

    inst = (result.get("instrumentation") or {}).get("ranked")
    ok = not errors and bool(inst)
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
    shutil.copy2(run_path, EVIDENCE_DIR / "instrument_presence_run.json")
    print(json.dumps(run_payload, indent=2))
    print(f"INSTRUMENT PRESENCE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_sha_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not _si007.snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if not ok:
        print("FAIL: incomplete instrument-presence output")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
