"""ACI-A2L-SI-002 isolated All-In-One rhythm + structure candidate.

Analyzes the locked mastered WAV with all-in-one-infer on CPU.
Uses mix-as-stems so Harmonix sees the finished mix without HTDemucs.
Does not modify ingest authority, approved lyrics, or release artifacts.
Does not create a Song Intelligence Record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
LOCKED_SOURCE = Path(
    r"C:\Users\tim\Desktop\Jays_stuff\2026_album\Masters - 24bit_48hz"
    r"\Masters  - 24bit_48hz\01Stomp to MIX MSTR 24bit_48hz.wav"
)
ENGINE_NAME = "all-in-one-infer"
DEFAULT_MODEL = "harmonix-all"
CANDIDATE_DIR_NAME = "all-in-one-infer"
ANALYSIS_PATH = "mix-as-stems"
ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = Path(os.environ.get("A2L_ALLINONE_CACHE", Path.home() / ".cache" / "a2l-all-in-one"))
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return jsonable(value.item())
        except Exception:
            pass
    start = getattr(value, "start", None)
    end = getattr(value, "end", None)
    label = getattr(value, "label", None)
    if start is not None and end is not None and label is not None:
        return {"start": jsonable(start), "end": jsonable(end), "label": jsonable(label)}
    return repr(value)


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def process_memory_bytes() -> dict:
    record = {
        "working_set_bytes": None,
        "peak_working_set_bytes": None,
        "sampler": "unavailable",
    }
    if sys.platform != "win32":
        return record
    import ctypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
    get_info.restype = ctypes.c_bool
    ok = get_info(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    if not ok:
        return record
    record.update(
        {
            "working_set_bytes": int(counters.WorkingSetSize),
            "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
            "sampler": "GetProcessMemoryInfo",
        }
    )
    return record


class MemorySampler:
    def __init__(self, interval: float = 0.5) -> None:
        self.interval = interval
        self.peak_working_set_bytes = 0
        self.samples = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        self._thread.join(timeout=5)
        final = process_memory_bytes()
        peak = max(self.peak_working_set_bytes, final.get("peak_working_set_bytes") or 0)
        return {
            "samples": self.samples,
            "sampled_peak_working_set_bytes": self.peak_working_set_bytes,
            "os_peak_working_set_bytes": final.get("peak_working_set_bytes"),
            "final_working_set_bytes": final.get("working_set_bytes"),
            "peak_working_set_bytes": peak or None,
            "peak_working_set_mb": round(peak / (1024 * 1024), 1) if peak else None,
            "sampler": final.get("sampler"),
        }

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            current = process_memory_bytes().get("working_set_bytes") or 0
            self.samples += 1
            if current > self.peak_working_set_bytes:
                self.peak_working_set_bytes = current


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def hardware_record() -> dict:
    cuda_available = False
    cuda_name = None
    torch_version = None
    try:
        import torch

        torch_version = torch.__version__
        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            cuda_name = torch.cuda.get_device_name(0)
    except Exception as exc:
        cuda_name = f"torch_probe_failed: {exc}"
    return {
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "torch": torch_version,
        "torch_cuda_available": cuda_available,
        "torch_cuda_device": cuda_name,
        "device": "cpu",
        "nvidia_smi": "not_found_on_path",
        "notes": (
            "No NVIDIA GPU/driver is treated as available. Analysis is forced to CPU. "
            "Target hardware is a normal consumer laptop."
        ),
    }


def package_versions() -> dict:
    names = [
        "all-in-one-infer",
        "demucs-infer",
        "madmom-infer",
        "torch",
        "torchaudio",
        "librosa",
        "numpy",
        "scipy",
        "soundfile",
        "huggingface_hub",
        "hydra-core",
        "omegaconf",
    ]
    found = {}
    from importlib.metadata import PackageNotFoundError, version

    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def protected_roots(sha: str) -> list[Path]:
    job = ROOT / "artifacts" / "ingest" / sha
    return [
        job / "authoritative_source",
        job / "machine_transcription",
        job / "a2l_pipeline",
        job / "a2l_pipeline_parakeet",
        job / "song_release_record.json",
        ROOT / "artifacts" / "releases",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-009-evidence" / "approved_lyrics.txt",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-009-evidence" / "approved_lyrics.json",
    ]


def snapshot_protected(sha: str) -> dict:
    record = {}
    for root in protected_roots(sha):
        if not root.exists():
            record[str(root)] = {"exists": False, "files": {}}
            continue
        files = {}
        if root.is_file():
            files[str(root)] = sha256_file(root)
        else:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    files[str(path)] = sha256_file(path)
        record[str(root)] = {"exists": True, "files": files}
    return record


def snapshots_match(before: dict, after: dict) -> bool:
    return before == after


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


def isolate_model_cache() -> dict:
    hf_home = CACHE_ROOT / "huggingface"
    torch_home = CACHE_ROOT / "torch"
    hf_home.mkdir(parents=True, exist_ok=True)
    torch_home.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf_home)
    os.environ["TORCH_HOME"] = str(torch_home)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_home / "hub")
    return {
        "cache_root": str(CACHE_ROOT),
        "hf_home": str(hf_home),
        "torch_home": str(torch_home),
        "bytes_before": dir_size_bytes(CACHE_ROOT),
    }


def list_cache_hints(root: Path) -> dict:
    names = []
    if root.exists():
        for path in root.rglob("*"):
            lowered = path.name.lower()
            if any(token in lowered for token in ("htdemucs", "demucs", "harmonix", "allinone")):
                names.append(str(path))
    return {
        "htdemucs_or_demucs_paths": [name for name in names if "demucs" in name.lower()],
        "harmonix_or_allinone_paths": [
            name for name in names if "harmonix" in name.lower() or "allinone" in name.lower()
        ],
    }


def hook_separation_probes() -> dict:
    probes = {
        "separate_in_memory": 0,
        "demix": 0,
        "DemucsProvider": 0,
    }
    import allin1_infer.demix as demix_mod
    import allin1_infer.stems as stems_mod

    original_separate = stems_mod.separate_in_memory
    original_demix = demix_mod.demix
    original_provider = getattr(stems_mod, "DemucsProvider", None)

    def wrapped_separate(*args, **kwargs):
        probes["separate_in_memory"] += 1
        return original_separate(*args, **kwargs)

    def wrapped_demix(*args, **kwargs):
        probes["demix"] += 1
        return original_demix(*args, **kwargs)

    stems_mod.separate_in_memory = wrapped_separate
    demix_mod.demix = wrapped_demix
    if original_provider is not None:
        original_init = original_provider.__init__

        def wrapped_init(self, *args, **kwargs):
            probes["DemucsProvider"] += 1
            return original_init(self, *args, **kwargs)

        original_provider.__init__ = wrapped_init
    return probes


def summarize_result(result) -> dict:
    beats = list(getattr(result, "beats", []) or [])
    downbeats = list(getattr(result, "downbeats", []) or [])
    beat_positions = list(getattr(result, "beat_positions", []) or [])
    segments = []
    for segment in getattr(result, "segments", []) or []:
        start = float(segment.start)
        end = float(segment.end)
        label = str(segment.label)
        segments.append(
            {
                "start": start,
                "end": end,
                "label": label,
                "display": f"{format_timestamp(start)}–{format_timestamp(end)} {label}",
            }
        )
    bpm = getattr(result, "bpm", None)
    return {
        "bpm": bpm,
        "beats_count": len(beats),
        "downbeats_count": len(downbeats),
        "beat_positions_count": len(beat_positions),
        "beats": beats,
        "downbeats": downbeats,
        "beat_positions": beat_positions,
        "segments": segments,
        "structure_display": [item["display"] for item in segments],
    }


def write_readable_txt(path: Path, summary: dict, meta: dict) -> None:
    lines = [
        "MACHINE-DERIVED RHYTHM + STRUCTURE",
        "ACI-A2L-SI-002",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "Do not write these values into approved lyrics or release authority.",
        "",
        f"engine: {meta.get('engine')}",
        f"engine_version: {meta.get('engine_version')}",
        f"model: {meta.get('model')}",
        f"device: {meta.get('device')}",
        f"analysis_path: {meta.get('analysis_path')}",
        f"source_separation_invoked: {meta.get('source_separation_invoked')}",
        f"source_sha256: {meta.get('source_sha256')}",
        "",
        "INPUT MAPPING:",
        "Finished master mix presented as bass/drums/other/vocals without HTDemucs.",
        "Harmonix was trained on separated stems. This mapping is mix-first, not the official mixed-audio pipeline.",
        f"working_copy: {meta.get('working_copy_note') or 'derived 32-bit PCM for engine read'}",
        "",
        f"BPM: {summary.get('bpm') if summary.get('bpm') is not None else 'unavailable'}",
        f"BEATS: {summary.get('beats_count', 0)}",
        f"DOWNBEATS: {summary.get('downbeats_count', 0)}",
        "",
        "STRUCTURE:",
    ]
    structure = summary.get("structure_display") or []
    if structure:
        lines.extend(structure)
    else:
        lines.append("unavailable")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def configure_stdio() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def prepare_analysis_wav(source: Path, dest: Path) -> dict:
    """Write a 32-bit PCM working copy. madmom-infer cannot mmap 24-bit WAV."""
    import soundfile as sf

    info = sf.info(str(source))
    data, sample_rate = sf.read(str(source), dtype="float32", always_2d=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), data, sample_rate, subtype="PCM_32")
    return {
        "source_subtype": info.subtype,
        "source_samplerate": info.samplerate,
        "source_channels": info.channels,
        "source_frames": info.frames,
        "working_subtype": "PCM_32",
        "working_samplerate": sample_rate,
        "working_channels": int(data.shape[1]),
        "working_frames": int(data.shape[0]),
        "note": (
            "The locked master is 24-bit PCM. madmom-infer/scipy wavfile mmap cannot read "
            "3-byte samples. This working copy is 32-bit PCM at the same sample rate and "
            "channel count. The authoritative source was not modified."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-002 All-In-One candidate")
    parser.add_argument("--source", type=Path, default=LOCKED_SOURCE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/all-in-one-infer/<sha256>/",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdio()
    args = parse_args()
    source = args.source
    if not source.is_file():
        print(f"FAIL: locked source not found: {source}")
        return 1

    before_sha = sha256_file(source)
    if before_sha != LOCKED_SHA256:
        print(f"FAIL: locked source SHA mismatch: {before_sha}")
        return 1

    ingest_source = (
        ROOT
        / "artifacts"
        / "ingest"
        / LOCKED_SHA256
        / "authoritative_source"
        / "source.wav"
    )
    ingest_before = sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_before = snapshot_protected(LOCKED_SHA256)

    out_dir = args.output_dir or (ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / LOCKED_SHA256)
    working_dir = out_dir / "working"
    engine_out = out_dir / "engine_out"
    working_dir.mkdir(parents=True, exist_ok=True)
    engine_out.mkdir(parents=True, exist_ok=True)

    working_copy = working_dir / "source_pcm32.wav"
    conversion = prepare_analysis_wav(source, working_copy)
    working_sha = sha256_file(working_copy)
    if working_sha == LOCKED_SHA256:
        print("FAIL: derived working copy unexpectedly matches locked 24-bit source")
        return 1

    raw_path = out_dir / "all_in_one_raw.json"
    txt_path = out_dir / "all_in_one_readable.txt"
    run_path = out_dir / "all_in_one_run.json"
    for path in (raw_path, txt_path, run_path, working_copy):
        assert_isolated_output(path, LOCKED_SHA256)

    cache_info = isolate_model_cache()
    versions = package_versions()
    hw = hardware_record()
    errors: list[str] = []
    summary: dict = {}
    probes = {}
    analysis_seconds = None
    model_load_note = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = MemorySampler()
    sampler.start()
    try:
        probes = hook_separation_probes()
        from allin1_infer import analyze
        from allin1_infer.stems_input import StemsInput

        stems = StemsInput(
            bass=working_copy,
            drums=working_copy,
            other=working_copy,
            vocals=working_copy,
            identifier="jay-master-mix-as-stems",
        )
        analyze_started = time.perf_counter()
        result = analyze(
            stems_input=stems,
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
        summary = summarize_result(result)
        model_load_note = "included_in_analysis_seconds"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = sha256_file(source)
    ingest_after = sha256_file(ingest_source) if ingest_source.is_file() else None
    working_after = sha256_file(working_copy)
    protected_after = snapshot_protected(LOCKED_SHA256)
    cache_bytes_after = dir_size_bytes(CACHE_ROOT)
    cache_hints = list_cache_hints(CACHE_ROOT)
    venv_dir = ROOT / ".venv-all-in-one"
    source_separation_invoked = bool(
        probes.get("separate_in_memory") or probes.get("demix") or probes.get("DemucsProvider")
    )
    htdemucs_cache_present = bool(cache_hints["htdemucs_or_demucs_paths"])

    raw_payload = {
        "candidate": "ACI-A2L-SI-002",
        "authority": "MACHINE-DERIVED",
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "engine": ENGINE_NAME,
        "engine_version": versions.get("all-in-one-infer"),
        "model": args.model,
        "license": "MIT",
        "analysis_path": ANALYSIS_PATH,
        "analysis_path_note": (
            "Official all-in-one-infer mixed-audio analyze() invokes HTDemucs. "
            "This spike used direct stems input with the finished mix mapped to all four stem slots, "
            "which bypasses Demucs model loading."
        ),
        "source_separation_invoked": source_separation_invoked,
        "source_separation_probes": probes,
        "htdemucs_cache_present": htdemucs_cache_present,
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
        "source_bytes": source.stat().st_size,
        "analysis_seconds": analysis_seconds,
        "model_load_note": model_load_note,
        "package_versions": versions,
        "hardware": hw,
        "cache": {
            **cache_info,
            "bytes_after": cache_bytes_after,
            "bytes_added": cache_bytes_after - cache_info["bytes_before"],
            "hints": cache_hints,
        },
        "venv_bytes": dir_size_bytes(venv_dir) if venv_dir.exists() else None,
        "memory": memory,
        "errors": errors,
        "rhythm_structure": summary,
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
            "source_separation_invoked": source_separation_invoked,
            "source_sha256": after_sha,
            "working_copy_note": conversion.get("note"),
        },
    )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "all_in_one_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "all_in_one_readable.txt")

    source_sha_unchanged = (
        before_sha == after_sha == LOCKED_SHA256
        and working_sha == working_after
        and working_after != LOCKED_SHA256
        and (ingest_before is None or ingest_before == ingest_after == LOCKED_SHA256)
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not errors and bool(summary),
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_sha_unchanged,
        "protected_artifacts_unchanged": snapshots_match(protected_before, protected_after),
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "source_separation_invoked": source_separation_invoked,
        "analysis_seconds": analysis_seconds,
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "all_in_one_run.json")

    print(json.dumps(run_payload, indent=2))
    print(f"ALL-IN-ONE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_sha_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
