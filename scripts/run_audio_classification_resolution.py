"""ACI-A2L-SI-008 isolated CLAP classification-resolution diagnostic.

Compares SI-007 CONTROL against equivalent richer prompts, a small
prompt ensemble, and per-window aggregation. Does not reopen Energy.
Does not change the master. Does not replace CLAP with another model.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI007_SCRIPT = ROOT / "scripts" / "run_audio_intelligence_candidate.py"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-008-evidence"
CANDIDATE_DIR_NAME = "clap-classification-resolution"
CONTROL_METHOD = (
    "SI-007 CONTROL: EOS-token text projection, mean-pooled 10s audio embeddings, "
    "cosine ranking, original SI-007 prompt templates"
)
RESOLUTION_RULE = (
    "For each category, select the method with the highest top_margin "
    "(rank-1 cosine minus rank-2 cosine). Tie-break: higher spread, then simpler method. "
    "Selection maximizes discrimination, not a preferred label."
)
MARGIN_WIN = 0.015
MARGIN_PARTIAL = 0.008
SPREAD_PARTIAL_GAIN = 0.020
TEXT_COLLAPSED = 0.990
TARGET_CATEGORIES = (
    "instrumentation",
    "genre_style",
    "vocal_character",
    "acoustic_electronic",
)
METHOD_ORDER = ("control", "bare", "rich", "ensemble", "window_mean")

# Equivalent templates. Every label in a category gets the same pattern.
RICH_TEMPLATES = {
    "instrumentation": "music featuring {label}",
    "genre_style": "a {label} music recording",
    "vocal_character": "music with {label}",
    "acoustic_electronic": "{label} music",
}
ENSEMBLE_TEMPLATES = {
    "instrumentation": (
        "music featuring {label}",
        "a recording with {label}",
        "{label} can be heard in this music",
    ),
    "genre_style": (
        "a {label} music recording",
        "{label} music",
        "this is {label} music",
    ),
    "vocal_character": (
        "music with {label}",
        "a recording with {label}",
        "{label} can be heard in this music",
    ),
    "acoustic_electronic": (
        "{label} music",
        "a {label} recording",
        "this music is {label}",
    ),
}


def load_si007():
    spec = importlib.util.spec_from_file_location("run_audio_intelligence_candidate", SI007_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def pairwise_cosines(vectors: list[list[float]]) -> list[float]:
    values = []
    for i, left in enumerate(vectors):
        for right in vectors[i + 1 :]:
            values.append(_si007.cosine_similarity(left, right))
    return values


def text_distinctness(vectors: list[list[float]]) -> dict:
    pairs = pairwise_cosines(vectors)
    if not pairs:
        return {
            "pair_count": 0,
            "mean_pairwise_cosine": None,
            "min_pairwise_cosine": None,
            "max_pairwise_cosine": None,
            "collapsed": True,
        }
    mean = sum(pairs) / len(pairs)
    return {
        "pair_count": len(pairs),
        "mean_pairwise_cosine": mean,
        "min_pairwise_cosine": min(pairs),
        "max_pairwise_cosine": max(pairs),
        "collapsed": mean >= TEXT_COLLAPSED,
    }


def separation_metrics(ranked: list[dict]) -> dict:
    if not ranked:
        return {"top_margin": None, "spread": None, "top1": None, "top2": None}
    scores = [row["cosine_similarity"] for row in ranked]
    top1 = ranked[0]["cosine_similarity"]
    top2 = ranked[1]["cosine_similarity"] if len(ranked) > 1 else None
    return {
        "top1": ranked[0]["label"],
        "top1_cosine": top1,
        "top2": ranked[1]["label"] if len(ranked) > 1 else None,
        "top2_cosine": top2,
        "top_margin": None if top2 is None else top1 - top2,
        "spread": max(scores) - min(scores),
        "max_cosine": max(scores),
        "min_cosine": min(scores),
    }


def format_ranked(rows: list[dict], limit: int | None = None) -> list[str]:
    lines = []
    shown = rows if limit is None else rows[:limit]
    for row in shown:
        lines.append(
            f"{row['rank']}. {row['display']:<28} cosine={row['cosine_similarity']:.4f}  "
            f"softmax={row['softmax_within_category']:.4f}"
        )
    return lines


def assess_category(control: dict, resolution: dict) -> dict:
    res_sep = resolution["separation"]
    ctl_sep = control["separation"]
    text = resolution.get("text_distinctness") or {}
    margin = res_sep.get("top_margin")
    spread = res_sep.get("spread") or 0.0
    control_spread = ctl_sep.get("spread") or 0.0
    spread_gain = spread - control_spread
    collapsed = bool(text.get("collapsed"))
    if collapsed or margin is None:
        result = "NO WIN"
        assessment = "UNSUPPORTED" if collapsed else "STILL WEAK"
    elif margin >= MARGIN_WIN:
        result = "WIN"
        assessment = "USEFUL"
    elif margin >= MARGIN_PARTIAL:
        result = "PARTIAL"
        assessment = "USEFUL"
    elif spread_gain >= SPREAD_PARTIAL_GAIN:
        result = "PARTIAL"
        assessment = "STILL WEAK"
    else:
        result = "NO WIN"
        assessment = "STILL WEAK"
    return {
        "category_result": result,
        "assessment": assessment,
        "top_margin": margin,
        "spread": spread,
        "spread_gain": spread_gain,
        "text_collapsed": collapsed,
    }


def pick_resolution(methods: dict[str, dict]) -> str:
    def key(name: str) -> tuple:
        sep = methods[name]["separation"]
        margin = sep.get("top_margin")
        spread = sep.get("spread")
        simplicity = METHOD_ORDER.index(name) if name in METHOD_ORDER else 99
        return (
            margin if margin is not None else -1.0,
            spread if spread is not None else -1.0,
            -simplicity,
        )

    return max(methods, key=key)


def engine3_result(category_results: dict[str, str]) -> str:
    wins = sum(1 for value in category_results.values() if value == "WIN")
    partials = sum(1 for value in category_results.values() if value == "PARTIAL")
    if wins >= 2:
        return "ENGINEERING WIN"
    if wins >= 1 or partials >= 2:
        return "PARTIAL PASS"
    return "CLAP SCOPE REDUCED"


def mean_vectors(vectors: list[list[float]]) -> list[float]:
    return _si007.mean_pool(vectors)


def embed_prompts(processor, model, prompts: list[str]) -> list[list[float]]:
    text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
    text_inputs = {key: value.to("cpu") for key, value in text_inputs.items()}
    return _si007.text_eos_embeddings(
        model, text_inputs["input_ids"], text_inputs["attention_mask"]
    ).tolist()


def embed_prompts_pooler(processor, model, prompts: list[str]) -> list[list[float]]:
    import torch.nn.functional as F

    text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
    text_inputs = {key: value.to("cpu") for key, value in text_inputs.items()}
    outputs = model.text_model(
        input_ids=text_inputs["input_ids"],
        attention_mask=text_inputs["attention_mask"],
    )
    projected = model.text_projection(outputs.pooler_output)
    return F.normalize(projected, dim=-1).detach().cpu().tolist()


def rank_from_items(audio_embed: list[float], items: list[dict], logit_scale: float) -> dict:
    ranked = _si007.rank_category(audio_embed, items, logit_scale)
    embeds = [item["embed"] for item in items]
    return {
        "ranked": ranked,
        "separation": separation_metrics(ranked),
        "text_distinctness": text_distinctness(embeds),
        "prompts": [item["prompt"] for item in items],
    }


def window_rank(
    chunk_embeds: list[list[float]],
    items: list[dict],
    logit_scale: float,
) -> dict:
    mean_scores = []
    win_counts = {item["label"]: 0 for item in items}
    for chunk in chunk_embeds:
        ranked = _si007.rank_category(chunk, items, logit_scale)
        if ranked:
            win_counts[ranked[0]["label"]] += 1
    for item in items:
        scores = [_si007.cosine_similarity(chunk, item["embed"]) for chunk in chunk_embeds]
        mean_scores.append({**item, "embed": item["embed"], "mean_window_cosine": sum(scores) / len(scores)})
    synthetic = []
    for item in mean_scores:
        synthetic.append(
            {
                "label": item["label"],
                "display": item["display"],
                "prompt": item["prompt"],
                "embed": item["embed"],
                "mean_window_cosine": item["mean_window_cosine"],
            }
        )
    # Rank using mean window cosine by substituting a dummy audio aligned to that score.
    # Direct sort keeps cosine_similarity field honest as the mean window cosine.
    synthetic.sort(key=lambda row: row["mean_window_cosine"], reverse=True)
    scored = []
    logits = []
    for item in synthetic:
        cosine = item["mean_window_cosine"]
        logit = float(logit_scale) * cosine
        logits.append(logit)
        scored.append(
            {
                "label": item["label"],
                "display": item["display"],
                "prompt": item["prompt"],
                "cosine_similarity": cosine,
                "clap_logit": logit,
            }
        )
    weights = _si007.softmax(logits)
    for row, weight in zip(scored, weights):
        row["softmax_within_category"] = weight
        row["score"] = row["cosine_similarity"]
        row["score_kind"] = "mean_window_cosine"
        row["window_rank1_count"] = win_counts[row["label"]]
    for index, row in enumerate(scored, start=1):
        row["rank"] = index
    embeds = [item["embed"] for item in items]
    return {
        "ranked": scored,
        "separation": separation_metrics(scored),
        "text_distinctness": text_distinctness(embeds),
        "prompts": [item["prompt"] for item in items],
        "window_rank1_counts": win_counts,
    }


def label_items(labels: list[str], prompts: list[str], embeds: list[list[float]]) -> list[dict]:
    items = []
    for label, prompt, embed in zip(labels, prompts, embeds):
        items.append(
            {
                "label": label,
                "display": _si007.display_label(label),
                "prompt": prompt,
                "embed": embed,
            }
        )
    return items


def analyze_resolution(source: Path) -> dict:
    import numpy as np
    import torch
    from transformers import ClapModel, ClapProcessor
    import librosa

    cache = _si007.isolate_model_cache()
    recorded_license = _si007.load_checkpoint_license()
    checkpoint_state = _si007.ensure_local_checkpoint()
    audio, sample_rate = librosa.load(str(source), sr=_si007.TARGET_SAMPLE_RATE, mono=True)
    ranges = _si007.chunk_ranges(len(audio), int(sample_rate))
    local_only = bool(checkpoint_state.get("local_files_only"))
    processor = ClapProcessor.from_pretrained(
        _si007.CHECKPOINT, revision=_si007.CHECKPOINT_REVISION, local_files_only=local_only
    )
    model = ClapModel.from_pretrained(
        _si007.CHECKPOINT, revision=_si007.CHECKPOINT_REVISION, local_files_only=local_only
    )
    model.to("cpu")
    model.eval()
    logit_scale = _si007.clap_logit_scale(model)

    chunk_embeds: list[list[float]] = []
    with torch.no_grad():
        for start, end in ranges:
            chunk = audio[start:end]
            if len(chunk) < int(_si007.CHUNK_SECONDS * sample_rate):
                padded = np.zeros(int(_si007.CHUNK_SECONDS * sample_rate), dtype=np.float32)
                padded[: len(chunk)] = chunk
                chunk = padded
            inputs = _si007.process_audio(processor, chunk, int(sample_rate))
            inputs = {key: value.to("cpu") for key, value in inputs.items()}
            features = model.get_audio_features(**inputs)
            embed = _si007.pooled_embedding(features)
            if embed.ndim == 2:
                embed = embed[0]
            chunk_embeds.append(embed.tolist())
    audio_embed = _si007.mean_pool(chunk_embeds)

    categories = {}
    embedding_validation = {"eos": {}, "pooler": {}}
    with torch.no_grad():
        for category in TARGET_CATEGORIES:
            labels = _si007.VOCABULARIES[category]
            control_prompts = [_si007.prompt_for(category, label) for label in labels]
            bare_prompts = [label for label in labels]
            rich_prompts = [RICH_TEMPLATES[category].format(label=label) for label in labels]
            control_embeds = embed_prompts(processor, model, control_prompts)
            bare_embeds = embed_prompts(processor, model, bare_prompts)
            rich_embeds = embed_prompts(processor, model, rich_prompts)
            pooler_embeds = embed_prompts_pooler(processor, model, control_prompts)

            ensemble_embeds = []
            ensemble_prompt_sets = []
            for label in labels:
                templates = [
                    template.format(label=label) for template in ENSEMBLE_TEMPLATES[category]
                ]
                ensemble_prompt_sets.append(templates)
                template_embeds = embed_prompts(processor, model, templates)
                ensemble_embeds.append(mean_vectors(template_embeds))

            control_items = label_items(labels, control_prompts, control_embeds)
            bare_items = label_items(labels, bare_prompts, bare_embeds)
            rich_items = label_items(labels, rich_prompts, rich_embeds)
            ensemble_items = label_items(
                labels,
                ["; ".join(prompts) for prompts in ensemble_prompt_sets],
                ensemble_embeds,
            )

            methods = {
                "control": rank_from_items(audio_embed, control_items, logit_scale),
                "bare": rank_from_items(audio_embed, bare_items, logit_scale),
                "rich": rank_from_items(audio_embed, rich_items, logit_scale),
                "ensemble": rank_from_items(audio_embed, ensemble_items, logit_scale),
                "window_mean": window_rank(chunk_embeds, control_items, logit_scale),
            }
            methods["control"]["template"] = _si007.PROMPT_TEMPLATES[category]
            methods["bare"]["template"] = "{label}"
            methods["rich"]["template"] = RICH_TEMPLATES[category]
            methods["ensemble"]["template"] = list(ENSEMBLE_TEMPLATES[category])
            methods["window_mean"]["template"] = _si007.PROMPT_TEMPLATES[category]
            methods["window_mean"]["aggregation"] = (
                "per-10s-window cosine then arithmetic mean; window rank-1 counts recorded"
            )

            selected = pick_resolution(methods)
            control_pack = methods["control"]
            resolution_pack = methods[selected]
            comparison = assess_category(control_pack, resolution_pack)
            categories[category] = {
                "methods": {
                    name: {
                        "ranked": pack["ranked"],
                        "separation": pack["separation"],
                        "text_distinctness": pack["text_distinctness"],
                        "template": pack.get("template"),
                        "prompts": pack.get("prompts"),
                        "aggregation": pack.get("aggregation"),
                        "window_rank1_counts": pack.get("window_rank1_counts"),
                    }
                    for name, pack in methods.items()
                },
                "selected_method": selected,
                "control": {
                    "ranked": control_pack["ranked"],
                    "separation": control_pack["separation"],
                    "text_distinctness": control_pack["text_distinctness"],
                    "template": control_pack["template"],
                },
                "resolution": {
                    "method": selected,
                    "ranked": resolution_pack["ranked"],
                    "separation": resolution_pack["separation"],
                    "text_distinctness": resolution_pack["text_distinctness"],
                    "template": resolution_pack.get("template"),
                },
                "assessment": comparison,
            }
            embedding_validation["eos"][category] = {
                "control": text_distinctness(control_embeds),
                "bare": text_distinctness(bare_embeds),
                "rich": text_distinctness(rich_embeds),
                "ensemble": text_distinctness(ensemble_embeds),
            }
            embedding_validation["pooler"][category] = text_distinctness(pooler_embeds)

    category_results = {
        category: payload["assessment"]["category_result"] for category, payload in categories.items()
    }
    return {
        "license": recorded_license,
        "cache": cache,
        "checkpoint_state": checkpoint_state,
        "logit_scale": logit_scale,
        "chunk_count": len(chunk_embeds),
        "duration_seconds": float(len(audio) / sample_rate) if sample_rate else None,
        "sample_rate": int(sample_rate),
        "embedding_validation": embedding_validation,
        "categories": categories,
        "category_results": category_results,
        "engine3_result": engine3_result(category_results),
        "selection_rule": RESOLUTION_RULE,
        "thresholds": {
            "margin_win": MARGIN_WIN,
            "margin_partial": MARGIN_PARTIAL,
            "spread_partial_gain": SPREAD_PARTIAL_GAIN,
            "text_collapsed": TEXT_COLLAPSED,
        },
    }


def write_readable(path: Path, result: dict, meta: dict) -> None:
    titles = _si007.CATEGORY_TITLES
    lines = [
        "MACHINE-DERIVED CLAP CLASSIFICATION RESOLUTION",
        "ACI-A2L-SI-008",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "Energy / Intensity was not reopened.",
        "CONTROL is the SI-007 method. RESOLUTION is selected by top_margin, not preferred labels.",
        "",
        f"engine: {_si007.ENGINE_NAME}",
        f"checkpoint: {_si007.CHECKPOINT}",
        f"revision: {_si007.CHECKPOINT_REVISION}",
        f"license: {meta.get('license')}",
        f"source_sha256: {meta.get('source_sha256')}",
        f"engine3_result: {result.get('engine3_result')}",
        f"selection_rule: {RESOLUTION_RULE}",
        "",
        "TEXT EMBEDDING VALIDATION",
        "EOS-token projection is the selected path. Hugging Face ClapTextPooler is diagnostic-only.",
    ]
    pooler = (result.get("embedding_validation") or {}).get("pooler") or {}
    eos = (result.get("embedding_validation") or {}).get("eos") or {}
    for category in TARGET_CATEGORIES:
        pooler_mean = (pooler.get(category) or {}).get("mean_pairwise_cosine")
        eos_mean = ((eos.get(category) or {}).get("control") or {}).get("mean_pairwise_cosine")
        lines.append(
            f"{titles[category]}: pooler_mean_pairwise={pooler_mean}  "
            f"eos_control_mean_pairwise={eos_mean}"
        )
    lines.append("")
    for category in TARGET_CATEGORIES:
        payload = (result.get("categories") or {}).get(category) or {}
        control = payload.get("control") or {}
        resolution = payload.get("resolution") or {}
        assessment = payload.get("assessment") or {}
        lines.append(titles[category])
        lines.append(f"CONTROL METHOD: {CONTROL_METHOD}")
        lines.append(f"CONTROL TEMPLATE: {control.get('template')}")
        lines.extend(format_ranked(control.get("ranked") or []))
        lines.append(
            "CONTROL SEPARATION: "
            f"top_margin={((control.get('separation') or {}).get('top_margin'))}  "
            f"spread={((control.get('separation') or {}).get('spread'))}"
        )
        lines.append(f"RESOLUTION METHOD: {resolution.get('method')}")
        lines.append(f"RESOLUTION TEMPLATE: {resolution.get('template')}")
        lines.extend(format_ranked(resolution.get("ranked") or []))
        lines.append(
            "RESOLUTION SEPARATION: "
            f"top_margin={((resolution.get('separation') or {}).get('top_margin'))}  "
            f"spread={((resolution.get('separation') or {}).get('spread'))}"
        )
        lines.append(
            "SEPARATION CHANGE: "
            f"top_margin_delta="
            f"{((resolution.get('separation') or {}).get('top_margin') or 0) - ((control.get('separation') or {}).get('top_margin') or 0):.6f}  "
            f"spread_delta={assessment.get('spread_gain')}"
        )
        lines.append(f"ASSESSMENT: {assessment.get('assessment')}")
        lines.append(f"CATEGORY RESULT: {assessment.get('category_result')}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-008 CLAP classification resolution")
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
    protected_before = _si007.snapshot_protected(_si007.LOCKED_SHA256)
    si007_evidence = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-007-evidence"
    si007_before = {}
    if si007_evidence.exists():
        for path in sorted(si007_evidence.rglob("*")):
            if path.is_file():
                si007_before[str(path)] = _si007.sha256_file(path)

    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / _si007.LOCKED_SHA256
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "classification_resolution_raw.json"
    txt_path = out_dir / "classification_resolution_readable.txt"
    run_path = out_dir / "classification_resolution_run.json"
    for path in (raw_path, txt_path, run_path):
        _si007.assert_isolated_output(path, _si007.LOCKED_SHA256)
        if si007_evidence.resolve() in path.resolve().parents:
            raise SystemExit("Refusing to write into SI-007 evidence")

    errors: list[str] = []
    result: dict = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = _si007.MemorySampler()
    sampler.start()
    try:
        started = __import__("time").perf_counter()
        result = analyze_resolution(source)
        analysis_seconds = __import__("time").perf_counter() - started
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = _si007.sha256_file(source)
    ingest_after = _si007.sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_after = _si007.snapshot_protected(_si007.LOCKED_SHA256)
    si007_after = {}
    if si007_evidence.exists():
        for path in sorted(si007_evidence.rglob("*")):
            if path.is_file():
                si007_after[str(path)] = _si007.sha256_file(path)

    raw_payload = {
        "candidate": "ACI-A2L-SI-008",
        "authority": {
            "master_wav": "AUTHORITATIVE INPUT",
            "clap_similarity": "MACHINE-DERIVED",
            "category_interpretation": "MACHINE-DERIVED",
        },
        "energy_reopened": False,
        "song_intelligence_record_created": False,
        "engine": _si007.ENGINE_NAME,
        "checkpoint": _si007.CHECKPOINT,
        "checkpoint_revision": _si007.CHECKPOINT_REVISION,
        "control_method": CONTROL_METHOD,
        "resolution_rule": RESOLUTION_RULE,
        "rich_templates": RICH_TEMPLATES,
        "ensemble_templates": ENSEMBLE_TEMPLATES,
        "control_templates": _si007.PROMPT_TEMPLATES,
        "vocabularies": _si007.VOCABULARIES,
        "gpu_required": False,
        "cloud_required": False,
        "device": "cpu",
        "source_path": str(source),
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "ingest_source_sha256_before": ingest_before,
        "ingest_source_sha256_after": ingest_after,
        "analysis_seconds": analysis_seconds,
        "package_versions": _si007.package_versions(),
        "hardware": _si007.hardware_record(),
        "memory": memory,
        "errors": errors,
        "resolution": result,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable(
        txt_path,
        result,
        {
            "license": result.get("license") or _si007.LICENSE_DECLARED,
            "source_sha256": after_sha,
        },
    )
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "classification_resolution_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "classification_resolution_readable.txt")

    source_unchanged = before_sha == after_sha == _si007.LOCKED_SHA256 and (
        ingest_before is None or ingest_before == ingest_after == _si007.LOCKED_SHA256
    )
    si007_unchanged = si007_before == si007_after
    ok = (
        not errors
        and bool(result.get("categories"))
        and all(category in (result.get("categories") or {}) for category in TARGET_CATEGORIES)
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_unchanged,
        "protected_artifacts_unchanged": _si007.snapshots_match(protected_before, protected_after),
        "si007_evidence_unchanged": si007_unchanged,
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "download_required": not bool((result.get("checkpoint_state") or {}).get("local_files_only")),
        "analysis_seconds": analysis_seconds,
        "engine3_result": result.get("engine3_result"),
        "category_results": result.get("category_results"),
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "classification_resolution_run.json")
    print(json.dumps(run_payload, indent=2))
    print(f"CLASSIFICATION RESOLUTION READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not _si007.snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if not si007_unchanged:
        print("FAIL: SI-007 evidence changed")
        return 1
    if not ok:
        print("FAIL: incomplete classification resolution")
        return 1
    return 0


_si007 = load_si007()

if __name__ == "__main__":
    raise SystemExit(main())
