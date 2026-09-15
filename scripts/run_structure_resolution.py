"""ACI-A2L-SI-003 structure resolution: diagnostic official All-In-One mixed path.

Does not rebuild SI-002 rhythm. Mix-as-stems remains the rhythm evidence.
This run uses official mixed-audio analyze(), which invokes HTDemucs as
analyzer plumbing only. That dependency is not accepted as an A2L capability.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI002_SCRIPT = ROOT / "scripts" / "run_all_in_one_candidate.py"
ENGINE_NAME = "all-in-one-infer"
DEFAULT_MODEL = "harmonix-all"
ANALYSIS_PATH = "official-mixed-htdemucs-diagnostic"
CANDIDATE_DIR_NAME = "all-in-one-infer"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-003-evidence"
SI002_EVIDENCE = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence"

INVESTIGATION = {
    "A_mixed_path_without_separation": {
        "result": "not_available",
        "reason": (
            "Harmonix AllInOne consumes a K=4 instrument log-spectrogram stack and uses "
            "cross-instrument attention. HarmonixConfig sets demixed=True and num_instruments=4. "
            "allin1_infer.analyze() on a mixed file always selects HTDemucs unless stems are supplied. "
            "There is no mix-only structure inference path."
        ),
    },
    "B_config_without_fabricating_stems": {
        "result": "not_available",
        "reason": (
            "StemsInput requires four existing wav files. SI-002 mix-as-stems presented the finished "
            "mix as bass/drums/other/vocals and returned chorus-collapsed labels. Substituting silence "
            "or zeros would also be fabricated input. No remaining configuration yields trained-distribution "
            "stem spectrograms without source separation or precomputed stems."
        ),
    },
    "C_alternate_structure_engine": {
        "result": "not_started",
        "reason": (
            "Deferred unless the All-In-One trained mixed path cannot complete or remains unusable "
            "within the laptop constraint. This ACI does not implement a second Song Intelligence engine "
            "while Engine #1 structure is still being diagnosed."
        ),
    },
    "selected_path": ANALYSIS_PATH,
    "source_separation": "DIAGNOSTIC",
    "not_accepted_a2l_capability": True,
}


def load_si002():
    spec = importlib.util.spec_from_file_location("run_all_in_one_candidate", SI002_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def format_structure_rows(summary: dict) -> list[str]:
    rows = []
    for segment in summary.get("segments") or []:
        start = sio.format_timestamp(float(segment["start"]))
        end = sio.format_timestamp(float(segment["end"]))
        label = str(segment["label"])
        rows.append(f"{start}-{end} | {label}")
    return rows


sio = load_si002()


def write_readable_txt(path: Path, summary: dict, meta: dict) -> None:
    rows = format_structure_rows(summary)
    lines = [
        "MACHINE-DERIVED STRUCTURE",
        "ACI-A2L-SI-003",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "HTDemucs invocation is DIAGNOSTIC analyzer plumbing, not an A2L product capability.",
        "",
        f"engine: {meta.get('engine')}",
        f"engine_version: {meta.get('engine_version')}",
        f"model: {meta.get('model')}",
        f"device: {meta.get('device')}",
        f"analysis_path: {meta.get('analysis_path')}",
        f"source_separation: {meta.get('source_separation')}",
        f"source_sha256: {meta.get('source_sha256')}",
        "",
        "STRUCTURE:",
    ]
    if rows:
        lines.extend(rows)
    else:
        lines.append("unavailable")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-003 structure resolution")
    parser.add_argument("--source", type=Path, default=sio.LOCKED_SOURCE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/all-in-one-infer/<sha>/si-003-structure-resolution/",
    )
    return parser.parse_args()


def main() -> int:
    sio.configure_stdio()
    args = parse_args()
    source = args.source
    if not source.is_file():
        print(f"FAIL: locked source not found: {source}")
        return 1

    before_sha = sio.sha256_file(source)
    if before_sha != sio.LOCKED_SHA256:
        print(f"FAIL: locked source SHA mismatch: {before_sha}")
        return 1

    ingest_source = (
        ROOT / "artifacts" / "ingest" / sio.LOCKED_SHA256 / "authoritative_source" / "source.wav"
    )
    ingest_before = sio.sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_before = sio.snapshot_protected(sio.LOCKED_SHA256)
    si002_before = {
        str(path): sio.sha256_file(path)
        for path in sorted(SI002_EVIDENCE.glob("*"))
        if path.is_file()
    }

    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / sio.LOCKED_SHA256 / "si-003-structure-resolution"
    )
    working_dir = out_dir / "working"
    engine_out = out_dir / "engine_out"
    working_dir.mkdir(parents=True, exist_ok=True)
    engine_out.mkdir(parents=True, exist_ok=True)

    working_copy = working_dir / "source_pcm32.wav"
    conversion = sio.prepare_analysis_wav(source, working_copy)
    working_sha = sio.sha256_file(working_copy)

    raw_path = out_dir / "structure_raw.json"
    txt_path = out_dir / "structure_readable.txt"
    run_path = out_dir / "structure_run.json"
    for path in (raw_path, txt_path, run_path, working_copy):
        sio.assert_isolated_output(path, sio.LOCKED_SHA256)
        if SI002_EVIDENCE.resolve() in path.resolve().parents or path.resolve().parent == SI002_EVIDENCE.resolve():
            raise SystemExit(f"Refusing to write into SI-002 evidence: {path}")

    cache_info = sio.isolate_model_cache()
    versions = sio.package_versions()
    hw = sio.hardware_record()
    errors: list[str] = []
    summary: dict = {}
    probes = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = sio.MemorySampler()
    sampler.start()
    try:
        probes = sio.hook_separation_probes()
        from allin1_infer import analyze

        analyze_started = time.perf_counter()
        result = analyze(
            paths=working_copy,
            out_dir=engine_out,
            visualize=False,
            sonify=False,
            model=args.model,
            device="cpu",
            include_activations=False,
            include_embeddings=False,
            demix_dir=out_dir / "demix",
            spec_dir=out_dir / "spec",
            keep_byproducts=False,
            overwrite=True,
            multiprocess=False,
        )
        analysis_seconds = time.perf_counter() - analyze_started
        summary = sio.summarize_result(result)
        summary["structure_rows"] = format_structure_rows(summary)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = sio.sha256_file(source)
    ingest_after = sio.sha256_file(ingest_source) if ingest_source.is_file() else None
    working_after = sio.sha256_file(working_copy)
    protected_after = sio.snapshot_protected(sio.LOCKED_SHA256)
    si002_after = {
        str(path): sio.sha256_file(path)
        for path in sorted(SI002_EVIDENCE.glob("*"))
        if path.is_file()
    }
    cache_bytes_after = sio.dir_size_bytes(sio.CACHE_ROOT)
    cache_hints = sio.list_cache_hints(sio.CACHE_ROOT)
    venv_dir = ROOT / ".venv-all-in-one"
    source_separation_invoked = bool(
        probes.get("separate_in_memory") or probes.get("demix") or probes.get("DemucsProvider")
    )

    raw_payload = {
        "candidate": "ACI-A2L-SI-003",
        "authority": "MACHINE-DERIVED",
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "htdemucs_accepted_as_a2l_capability": False,
        "engine": ENGINE_NAME,
        "engine_version": versions.get("all-in-one-infer"),
        "model": args.model,
        "license": "MIT (all-in-one-infer); HTDemucs weights via demucs-infer (Meta Demucs lineage)",
        "analysis_path": ANALYSIS_PATH,
        "investigation": INVESTIGATION,
        "source_separation": "DIAGNOSTIC" if source_separation_invoked or not errors else "FAILED",
        "source_separation_invoked": source_separation_invoked,
        "source_separation_probes": probes,
        "htdemucs_cache_present": bool(cache_hints["htdemucs_or_demucs_paths"]),
        "gpu_required": False,
        "cloud_required": False,
        "device": "cpu",
        "source_path": str(source),
        "working_copy": str(working_copy),
        "working_copy_conversion": conversion,
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "ingest_source_sha256_before": ingest_before,
        "ingest_source_sha256_after": ingest_after,
        "working_copy_sha256_before": working_sha,
        "working_copy_sha256_after": working_after,
        "si002_evidence_unchanged": si002_before == si002_after,
        "analysis_seconds": analysis_seconds,
        "package_versions": versions,
        "hardware": hw,
        "cache": {
            **cache_info,
            "bytes_after": cache_bytes_after,
            "bytes_added": cache_bytes_after - cache_info["bytes_before"],
            "hints": cache_hints,
        },
        "venv_bytes": sio.dir_size_bytes(venv_dir) if venv_dir.exists() else None,
        "memory": memory,
        "errors": errors,
        "rhythm_structure": summary,
        "si002_structure_preserved_for_comparison": [
            "00:00-00:02 | start",
            "00:02-00:19 | chorus",
            "00:19-00:36 | verse",
            "00:36-01:10 | chorus",
            "01:10-01:30 | chorus",
            "01:30-01:54 | chorus",
            "01:54-02:23 | chorus",
            "02:23-02:42 | chorus",
            "02:42-02:57 | chorus",
            "02:57-03:20 | chorus",
            "03:20-03:27 | end",
        ],
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        summary,
        {
            "engine": ENGINE_NAME,
            "engine_version": versions.get("all-in-one-infer"),
            "model": args.model,
            "device": "cpu",
            "analysis_path": ANALYSIS_PATH,
            "source_separation": raw_payload["source_separation"],
            "source_sha256": after_sha,
        },
    )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "structure_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "structure_readable.txt")

    source_sha_unchanged = (
        before_sha == after_sha == sio.LOCKED_SHA256
        and working_sha == working_after
        and (ingest_before is None or ingest_before == ingest_after == sio.LOCKED_SHA256)
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not errors and bool(summary),
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_sha_unchanged,
        "protected_artifacts_unchanged": sio.snapshots_match(protected_before, protected_after),
        "si002_evidence_unchanged": si002_before == si002_after,
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "source_separation": raw_payload["source_separation"],
        "analysis_seconds": analysis_seconds,
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "structure_run.json")

    print(json.dumps(run_payload, indent=2))
    print(f"STRUCTURE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_sha_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not sio.snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if si002_before != si002_after:
        print("FAIL: SI-002 evidence changed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
