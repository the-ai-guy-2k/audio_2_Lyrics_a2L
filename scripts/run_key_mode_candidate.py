"""ACI-A2L-SI-004 isolated Key + Mode candidate.

Estimates musical key and major/minor mode from the locked mastered mix
using librosa chroma_cqt and Krumhansl-Kessler / Krumhansl-Schmuckler
template correlation. Does not detect chords. Does not use Essentia or
madmom neural key models. Does not modify ingest or release authority.
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
ENGINE_NAME = "librosa chroma_cqt + Krumhansl-Schmuckler"
METHOD = "chroma_cqt mean vector correlated with Krumhansl-Kessler major/minor profiles"
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl & Kessler (1982), as used by the Krumhansl-Schmuckler key-finding algorithm.
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
CANDIDATE_DIR_NAME = "key-mode"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-004-evidence"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("pearson requires equal non-empty vectors")
    n = len(left)
    mean_l = sum(left) / n
    mean_r = sum(right) / n
    num = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right))
    den_l = sum((a - mean_l) ** 2 for a in left) ** 0.5
    den_r = sum((b - mean_r) ** 2 for b in right) ** 0.5
    if den_l == 0 or den_r == 0:
        return 0.0
    return num / (den_l * den_r)


def rotate(values: list[float], steps: int) -> list[float]:
    """Right-rotate so profile tonic (index 0) lands on chroma bin `steps`."""
    n = len(values)
    steps = steps % n
    if steps == 0:
        return list(values)
    return values[-steps:] + values[:-steps]


def estimate_key_from_chroma(chroma_mean: list[float], top_n: int = 5) -> dict:
    if len(chroma_mean) != 12:
        raise ValueError("chroma_mean must have 12 pitch-class bins")
    scored = []
    for tonic, name in enumerate(PITCH_CLASSES):
        major = pearson(chroma_mean, rotate(KK_MAJOR, tonic))
        minor = pearson(chroma_mean, rotate(KK_MINOR, tonic))
        scored.append({"key": name, "mode": "major", "score": major})
        scored.append({"key": name, "mode": "minor", "score": minor})
    scored.sort(key=lambda item: item["score"], reverse=True)
    best = scored[0]
    second = scored[1] if len(scored) > 1 else {"score": 0.0}
    worst = scored[-1]
    spread = best["score"] - worst["score"]
    margin = best["score"] - second["score"]
    confidence = margin / spread if spread else 0.0
    return {
        "key": best["key"],
        "mode": best["mode"],
        "score": best["score"],
        "confidence": confidence,
        "margin_over_runner_up": margin,
        "alternates": scored[:top_n],
    }


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


def hardware_record() -> dict:
    return {
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "device": "cpu",
        "notes": "Key + Mode analysis is CPU-only. No neural key model is downloaded.",
    }


def package_versions() -> dict:
    names = ["librosa", "numpy", "scipy", "soundfile", "audioread"]
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
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-003-evidence",
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


def analyze_mix(path: Path) -> dict:
    import librosa

    audio, sample_rate = librosa.load(str(path), sr=None, mono=True)
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sample_rate)
    chroma_mean = [float(value) for value in chroma.mean(axis=1)]
    estimate = estimate_key_from_chroma(chroma_mean)
    estimate["chroma_mean"] = chroma_mean
    estimate["sample_rate"] = int(sample_rate)
    estimate["duration_seconds"] = float(len(audio) / sample_rate) if sample_rate else None
    estimate["chroma_frames"] = int(chroma.shape[1])
    return estimate


def write_readable_txt(path: Path, estimate: dict, meta: dict) -> None:
    alternates = estimate.get("alternates") or []
    alt_lines = [
        f"  {item['key']} {item['mode']}  score={item['score']:.4f}" for item in alternates
    ]
    confidence = estimate.get("confidence")
    lines = [
        "MACHINE-DERIVED KEY + MODE",
        "ACI-A2L-SI-004",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "Chords were not estimated.",
        "",
        f"engine: {meta.get('engine')}",
        f"method: {meta.get('method')}",
        f"librosa: {meta.get('librosa_version')}",
        f"device: cpu",
        f"source_sha256: {meta.get('source_sha256')}",
        "",
        f"KEY: {estimate.get('key', 'unavailable')}",
        f"MODE: {estimate.get('mode', 'unavailable')}",
        f"CONFIDENCE: {confidence if confidence is not None else 'unavailable'}",
        f"SCORE: {estimate.get('score')}",
        "",
        "ALTERNATE CANDIDATES:",
    ]
    lines.extend(alt_lines or ["  unavailable"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-004 Key + Mode candidate")
    parser.add_argument("--source", type=Path, default=LOCKED_SOURCE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/key-mode/<sha256>/",
    )
    return parser.parse_args()


def main() -> int:
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
        ROOT / "artifacts" / "ingest" / LOCKED_SHA256 / "authoritative_source" / "source.wav"
    )
    ingest_before = sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_before = snapshot_protected(LOCKED_SHA256)

    out_dir = args.output_dir or (ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / LOCKED_SHA256)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "key_mode_raw.json"
    txt_path = out_dir / "key_mode_readable.txt"
    run_path = out_dir / "key_mode_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, LOCKED_SHA256)

    versions = package_versions()
    hw = hardware_record()
    errors: list[str] = []
    estimate: dict = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = MemorySampler()
    sampler.start()
    try:
        analyze_started = time.perf_counter()
        estimate = analyze_mix(source)
        analysis_seconds = time.perf_counter() - analyze_started
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = sha256_file(source)
    ingest_after = sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_after = snapshot_protected(LOCKED_SHA256)
    venv_dir = ROOT / ".venv-key-mode"

    raw_payload = {
        "candidate": "ACI-A2L-SI-004",
        "authority": "MACHINE-DERIVED",
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "chords_estimated": False,
        "engine": ENGINE_NAME,
        "method": METHOD,
        "license": "librosa ISC; numpy/scipy BSD; Krumhansl-Kessler profiles from published literature",
        "rejected_candidates": [
            "Essentia KeyExtractor — AGPL / NC model concern",
            "madmom neural key recognition — NC pretrained weights",
        ],
        "gpu_required": False,
        "cloud_required": False,
        "device": "cpu",
        "source_path": str(source),
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "ingest_source_sha256_before": ingest_before,
        "ingest_source_sha256_after": ingest_after,
        "analysis_seconds": analysis_seconds,
        "package_versions": versions,
        "hardware": hw,
        "venv_bytes": dir_size_bytes(venv_dir) if venv_dir.exists() else None,
        "memory": memory,
        "errors": errors,
        "key_mode": estimate,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        estimate,
        {
            "engine": ENGINE_NAME,
            "method": METHOD,
            "librosa_version": versions.get("librosa"),
            "source_sha256": after_sha,
        },
    )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "key_mode_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "key_mode_readable.txt")

    source_sha_unchanged = before_sha == after_sha == LOCKED_SHA256 and (
        ingest_before is None or ingest_before == ingest_after == LOCKED_SHA256
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not errors and bool(estimate.get("key")),
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_sha_unchanged,
        "protected_artifacts_unchanged": snapshots_match(protected_before, protected_after),
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "analysis_seconds": analysis_seconds,
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "key_mode_run.json")

    print(json.dumps(run_payload, indent=2))
    print(f"KEY+MODE READABLE OUTPUT:\n{txt_path.resolve()}")
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
