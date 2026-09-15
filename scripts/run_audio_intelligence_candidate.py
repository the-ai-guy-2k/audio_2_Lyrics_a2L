"""ACI-A2L-SI-007 isolated Audio Intelligence candidate.

Zero-shot ranks bounded instrumentation, genre/style, vocal, and
acoustic/electronic labels with transformers ClapModel on
laion/larger_clap_music (Apache-2.0). Energy uses deterministic RMS
and onset-density measurements. Does not estimate chords, lyrics, or
create a Song Intelligence Record. Does not modify ingest or release
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
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
ENGINE_NAME = "transformers ClapModel"
CHECKPOINT = "laion/larger_clap_music"
CHECKPOINT_REVISION = "a0b4534a14f58e20944452dff00a22a06ce629d1"
LICENSE_DECLARED = "apache-2.0"
ALLOWED_LICENSES = {"apache-2.0"}
EXPECTED_WEIGHTS_SHA256 = "5c289311f4a030d768af7ffbfdecd01b008aa64824211899a4e59f4f9d154fd1"
EXPECTED_WEIGHTS_BYTES = 776444665
METHOD = (
    "mean-pooled 10s CLAP audio embeddings ranked against bounded text vocabularies; "
    "text vectors use EOS-token projection (LAION convention); energy from RMS and onset density"
)
SCORE_KIND = (
    "cosine_similarity is the ranking score; softmax_within_category is a within-list "
    "softmax of CLAP logits and is not a calibrated probability"
)
CANDIDATE_DIR_NAME = "clap-audio-intelligence"
CHUNK_SECONDS = 10.0
HOP_SECONDS = 10.0
MIN_CHUNK_SECONDS = 1.0
TARGET_SAMPLE_RATE = 48000
ENERGY_HIGH_RMS = 0.15
ENERGY_MEDIUM_RMS = 0.08
ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = Path(os.environ.get("A2L_CLAP_CACHE", Path.home() / ".cache" / "a2l-clap"))
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-007-evidence"

# Governed ACI-A2L-SI-007 vocabularies. Categories stay separate.
# Examples from the ACI are the label set; labels were not tuned after seeing audio.
VOCABULARIES = {
    "instrumentation": [
        "electric guitar",
        "acoustic guitar",
        "bass guitar",
        "drums",
        "percussion",
        "piano",
        "keyboard",
        "organ",
        "fiddle",
        "violin",
        "banjo",
        "harmonica",
        "synthesizer",
    ],
    "genre_style": [
        "country",
        "country rock",
        "southern rock",
        "rock",
        "blues",
        "funk",
        "pop",
        "americana",
        "roots rock",
    ],
    "vocal_character": [
        "vocals present",
        "predominantly instrumental",
        "male lead vocal",
        "female lead vocal",
        "prominent lead vocal",
        "backing vocals",
    ],
    "acoustic_electronic": [
        "predominantly acoustic",
        "mixed acoustic/electric",
        "predominantly electric",
        "electronic/synth-heavy",
    ],
}

PROMPT_TEMPLATES = {
    "instrumentation": "a song featuring {label}",
    "genre_style": "{label} music",
    "vocal_character": "a song with {label}",
    "acoustic_electronic": "{label} music",
}

CATEGORY_TITLES = {
    "instrumentation": "INSTRUMENTATION",
    "genre_style": "GENRE / STYLE",
    "vocal_character": "VOCAL CHARACTERISTICS",
    "acoustic_electronic": "ACOUSTIC / ELECTRONIC CHARACTER",
}


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


def display_label(label: str) -> str:
    return " ".join(part.capitalize() if part != "and" else part for part in label.split())


def prompt_for(category: str, label: str) -> str:
    return PROMPT_TEMPLATES[category].format(label=label)


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return list(vector)
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    a = l2_normalize(left)
    b = l2_normalize(right)
    return sum(x * y for x, y in zip(a, b))


def softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps)
    if total == 0:
        return [0.0 for _ in values]
    return [value / total for value in exps]


def mean_pool(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        raise ValueError("mean_pool requires at least one vector")
    dim = len(vectors[0])
    acc = [0.0] * dim
    for vector in vectors:
        normalized = l2_normalize(vector)
        for index, value in enumerate(normalized):
            acc[index] += value
    count = float(len(vectors))
    return l2_normalize([value / count for value in acc])


def chunk_ranges(
    n_samples: int,
    sample_rate: int,
    chunk_seconds: float = CHUNK_SECONDS,
    hop_seconds: float = HOP_SECONDS,
    min_seconds: float = MIN_CHUNK_SECONDS,
) -> list[tuple[int, int]]:
    if n_samples <= 0 or sample_rate <= 0:
        return []
    chunk = int(chunk_seconds * sample_rate)
    hop = int(hop_seconds * sample_rate)
    min_len = int(min_seconds * sample_rate)
    if n_samples <= chunk:
        return [(0, n_samples)]
    ranges = []
    start = 0
    while start < n_samples:
        end = min(start + chunk, n_samples)
        if end - start < min_len and ranges:
            break
        ranges.append((start, end))
        if end >= n_samples:
            break
        start += hop
    return ranges


def clap_logit_scale(model) -> float:
    """transformers 5.x ClapModel uses logit_scale_a / logit_scale_t, not logit_scale."""
    param = getattr(model, "logit_scale_a", None)
    if param is None:
        param = getattr(model, "logit_scale", None)
    if param is None:
        raise SystemExit("CLAP logit scale parameter missing")
    return float(param.exp().detach().cpu().item())


def pooled_embedding(features):
    if hasattr(features, "pooler_output"):
        tensor = features.pooler_output
    elif isinstance(features, (tuple, list)):
        tensor = features[0]
    else:
        tensor = features
    return tensor.detach().cpu()


def process_audio(processor, chunk, sample_rate: int):
    """transformers 4.x ClapProcessor uses audios=; 5.x uses audio=."""
    kwargs = {"sampling_rate": int(sample_rate), "return_tensors": "pt"}
    try:
        return processor(audios=chunk, **kwargs)
    except (TypeError, ValueError):
        return processor(audio=chunk, **kwargs)


def text_eos_embeddings(model, input_ids, attention_mask):
    """LAION CLAP uses the EOS token, not Hugging Face ClapTextPooler's first-token tanh pooler."""
    import torch
    import torch.nn.functional as F

    outputs = model.text_model(input_ids=input_ids, attention_mask=attention_mask)
    sequence = outputs.last_hidden_state
    eos_index = attention_mask.sum(dim=1) - 1
    eos_hidden = sequence[torch.arange(sequence.size(0), device=sequence.device), eos_index]
    projected = model.text_projection(eos_hidden)
    return F.normalize(projected, dim=-1).detach().cpu()


def rank_category(
    audio_embed: list[float],
    items: list[dict],
    logit_scale: float,
) -> list[dict]:
    scored = []
    logits = []
    for item in items:
        cosine = cosine_similarity(audio_embed, item["embed"])
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
    weights = softmax(logits)
    for row, weight in zip(scored, weights):
        row["softmax_within_category"] = weight
        row["score"] = row["cosine_similarity"]
        row["score_kind"] = "cosine_similarity"
    scored.sort(key=lambda row: row["cosine_similarity"], reverse=True)
    for index, row in enumerate(scored, start=1):
        row["rank"] = index
    return scored


def energy_label_from_rms(rms_mean: float) -> str:
    if rms_mean >= ENERGY_HIGH_RMS:
        return "HIGH ENERGY"
    if rms_mean >= ENERGY_MEDIUM_RMS:
        return "MEDIUM ENERGY"
    return "LOW ENERGY"


def measure_energy(audio, sample_rate: int) -> dict:
    import librosa
    import numpy as np

    duration = float(len(audio) / sample_rate) if sample_rate else 0.0
    rms = librosa.feature.rms(y=np.asarray(audio))[0]
    onset_times = librosa.onset.onset_detect(y=np.asarray(audio), sr=sample_rate, units="time")
    rms_mean = float(np.mean(rms)) if len(rms) else 0.0
    rms_peak = float(np.max(rms)) if len(rms) else 0.0
    onset_density = float(len(onset_times) / duration) if duration else 0.0
    label = energy_label_from_rms(rms_mean)
    return {
        "authority_measured": {
            "rms_mean": rms_mean,
            "rms_peak": rms_peak,
            "onset_count": int(len(onset_times)),
            "onset_density_per_second": onset_density,
            "duration_seconds": duration,
            "sample_rate": int(sample_rate),
        },
        "authority_machine_derived": {
            "energy_label": label,
            "rule": (
                f"HIGH ENERGY if rms_mean>={ENERGY_HIGH_RMS}; "
                f"MEDIUM ENERGY if rms_mean>={ENERGY_MEDIUM_RMS}; else LOW ENERGY. "
                "Not a loudness or mastering/QC judgment."
            ),
        },
    }


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


def ensure_local_checkpoint() -> dict:
    """Refuse incomplete snapshot weights. Reuse a complete blob when present."""
    repo = hub_repo_dir()
    snap = snapshot_dir() / "pytorch_model.bin"
    blob = repo / "blobs" / EXPECTED_WEIGHTS_SHA256
    record = {
        "expected_bytes": EXPECTED_WEIGHTS_BYTES,
        "expected_sha256": EXPECTED_WEIGHTS_SHA256,
        "blob_bytes": blob.stat().st_size if blob.is_file() else 0,
        "snapshot_bytes_before": snap.stat().st_size if snap.is_file() else 0,
        "action": "none",
        "local_files_only": False,
    }
    blob_ok = blob.is_file() and blob.stat().st_size == EXPECTED_WEIGHTS_BYTES
    snap_ok = snap.is_file() and snap.stat().st_size == EXPECTED_WEIGHTS_BYTES
    if snap_ok:
        record["action"] = "snapshot_complete"
        record["local_files_only"] = True
        return record
    if snap.is_file() and not snap_ok:
        snap.unlink()
        record["action"] = "deleted_incomplete_snapshot"
    if blob_ok:
        try:
            os.link(blob, snap)
            record["action"] = "hardlink_complete_blob_to_snapshot"
        except OSError:
            shutil.copy2(blob, snap)
            record["action"] = "copied_complete_blob_to_snapshot"
        record["local_files_only"] = snap.is_file() and snap.stat().st_size == EXPECTED_WEIGHTS_BYTES
        return record
    record["action"] = "download_required"
    record["local_files_only"] = False
    return record


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
    torch_version = None
    cuda_available = False
    try:
        import torch

        torch_version = torch.__version__
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        pass
    return {
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "torch": torch_version,
        "torch_cuda_available": cuda_available,
        "device": "cpu",
        "notes": (
            "Audio Intelligence is forced to CPU. GPU may exist but is not required. "
            "No cloud inference is used."
        ),
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
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-003-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-004-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-006-evidence",
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
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    return {
        "cache_root": str(CACHE_ROOT),
        "hf_home": str(hf_home),
        "torch_home": str(torch_home),
        "bytes_before": dir_size_bytes(CACHE_ROOT),
    }


def analyze_mix(path: Path) -> dict:
    cache = isolate_model_cache()
    import numpy as np
    import torch
    from transformers import ClapModel, ClapProcessor
    import librosa

    recorded_license = load_checkpoint_license()
    checkpoint_state = ensure_local_checkpoint()
    audio, sample_rate = librosa.load(str(path), sr=TARGET_SAMPLE_RATE, mono=True)
    energy = measure_energy(audio, int(sample_rate))
    ranges = chunk_ranges(len(audio), int(sample_rate))

    local_only = bool(checkpoint_state.get("local_files_only"))
    processor = ClapProcessor.from_pretrained(
        CHECKPOINT, revision=CHECKPOINT_REVISION, local_files_only=local_only
    )
    model = ClapModel.from_pretrained(
        CHECKPOINT, revision=CHECKPOINT_REVISION, local_files_only=local_only
    )
    model.to("cpu")
    model.eval()
    logit_scale = clap_logit_scale(model)

    chunk_embeds: list[list[float]] = []
    with torch.no_grad():
        for start, end in ranges:
            chunk = audio[start:end]
            if len(chunk) < int(CHUNK_SECONDS * sample_rate):
                padded = np.zeros(int(CHUNK_SECONDS * sample_rate), dtype=np.float32)
                padded[: len(chunk)] = chunk
                chunk = padded
            inputs = process_audio(processor, chunk, int(sample_rate))
            inputs = {key: value.to("cpu") for key, value in inputs.items()}
            features = model.get_audio_features(**inputs)
            embed = pooled_embedding(features)
            if embed.ndim == 2:
                embed = embed[0]
            chunk_embeds.append(embed.tolist())

    audio_embed = mean_pool(chunk_embeds)

    rankings = {}
    with torch.no_grad():
        for category, labels in VOCABULARIES.items():
            items = []
            prompts = [prompt_for(category, label) for label in labels]
            text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
            text_inputs = {key: value.to("cpu") for key, value in text_inputs.items()}
            text_embeds = text_eos_embeddings(
                model, text_inputs["input_ids"], text_inputs["attention_mask"]
            ).tolist()
            for label, prompt, embed in zip(labels, prompts, text_embeds):
                items.append(
                    {
                        "label": label,
                        "display": display_label(label),
                        "prompt": prompt,
                        "embed": embed,
                    }
                )
            rankings[category] = rank_category(audio_embed, items, logit_scale)

    return {
        "license": recorded_license,
        "cache": cache,
        "checkpoint_state": checkpoint_state,
        "cache_bytes_after": dir_size_bytes(CACHE_ROOT),
        "checkpoint_snapshot_bytes": dir_size_bytes(hub_repo_dir()),
        "logit_scale": logit_scale,
        "chunk_count": len(chunk_embeds),
        "chunk_ranges": [{"start": start, "end": end} for start, end in ranges],
        "sample_rate": int(sample_rate),
        "duration_seconds": float(len(audio) / sample_rate) if sample_rate else None,
        "rankings": rankings,
        "energy": energy,
        "score_kind": SCORE_KIND,
    }


def format_ranked_block(title: str, rows: list[dict]) -> list[str]:
    lines = [title]
    for row in rows:
        lines.append(
            f"{row['rank']}. {row['display']:<28} cosine={row['cosine_similarity']:.4f}  "
            f"softmax={row['softmax_within_category']:.4f}"
        )
    return lines


def write_readable_txt(path: Path, result: dict, meta: dict) -> None:
    rankings = result.get("rankings") or {}
    energy = result.get("energy") or {}
    measured = energy.get("authority_measured") or {}
    derived = energy.get("authority_machine_derived") or {}
    lines = [
        "MACHINE-DERIVED AUDIO INTELLIGENCE",
        "ACI-A2L-SI-007",
        "NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "CLAP rankings are MACHINE-DERIVED cosine similarities, not calibrated probabilities.",
        "Energy measurements are MEASURED. Energy labels are MACHINE-DERIVED.",
        "",
        f"engine: {meta.get('engine')}",
        f"checkpoint: {meta.get('checkpoint')}",
        f"revision: {meta.get('revision')}",
        f"license: {meta.get('license')}",
        f"device: cpu",
        f"source_sha256: {meta.get('source_sha256')}",
        f"score_kind: {SCORE_KIND}",
        "",
    ]
    for category in ("instrumentation", "genre_style", "vocal_character", "acoustic_electronic"):
        lines.extend(format_ranked_block(CATEGORY_TITLES[category], rankings.get(category) or []))
        lines.append("")
    lines.extend(
        [
            "ENERGY / INTENSITY",
            f"MEASURED rms_mean: {measured.get('rms_mean')}",
            f"MEASURED rms_peak: {measured.get('rms_peak')}",
            f"MEASURED onset_count: {measured.get('onset_count')}",
            f"MEASURED onset_density_per_second: {measured.get('onset_density_per_second')}",
            f"MACHINE-DERIVED label: {derived.get('energy_label')}",
            f"rule: {derived.get('rule')}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-007 Audio Intelligence candidate")
    parser.add_argument("--source", type=Path, default=LOCKED_SOURCE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/clap-audio-intelligence/<sha256>/",
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

    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / LOCKED_SHA256
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "audio_intelligence_raw.json"
    txt_path = out_dir / "audio_intelligence_readable.txt"
    run_path = out_dir / "audio_intelligence_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, LOCKED_SHA256)

    versions = package_versions()
    hw = hardware_record()
    errors: list[str] = []
    result: dict = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = MemorySampler()
    sampler.start()
    try:
        analyze_started = time.perf_counter()
        result = analyze_mix(source)
        analysis_seconds = time.perf_counter() - analyze_started
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_sha = sha256_file(source)
    ingest_after = sha256_file(ingest_source) if ingest_source.is_file() else None
    protected_after = snapshot_protected(LOCKED_SHA256)
    venv_dir = ROOT / ".venv-clap"

    raw_payload = {
        "candidate": "ACI-A2L-SI-007",
        "authority": {
            "master_wav": "AUTHORITATIVE INPUT",
            "clap_rankings": "MACHINE-DERIVED",
            "instrumentation": "MACHINE-DERIVED",
            "genre_style": "MACHINE-DERIVED",
            "vocal_character": "MACHINE-DERIVED",
            "acoustic_electronic": "MACHINE-DERIVED",
            "energy_measurements": "MEASURED",
            "energy_label": "MACHINE-DERIVED",
        },
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "chords_estimated": False,
        "lyric_intelligence": False,
        "engine": ENGINE_NAME,
        "checkpoint": CHECKPOINT,
        "checkpoint_revision": CHECKPOINT_REVISION,
        "model_source": f"https://huggingface.co/{CHECKPOINT}/tree/{CHECKPOINT_REVISION}",
        "method": METHOD,
        "license": result.get("license") or LICENSE_DECLARED,
        "score_kind": SCORE_KIND,
        "prompt_templates": PROMPT_TEMPLATES,
        "vocabularies": VOCABULARIES,
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
        "cache_bytes_after": result.get("cache_bytes_after"),
        "checkpoint_snapshot_bytes": result.get("checkpoint_snapshot_bytes"),
        "checkpoint_state": result.get("checkpoint_state"),
        "memory": memory,
        "errors": errors,
        "audio_intelligence": {
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
    shutil.copy2(raw_path, EVIDENCE_DIR / "audio_intelligence_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "audio_intelligence_readable.txt")

    rankings = result.get("rankings") or {}
    ok = (
        not errors
        and bool(rankings.get("instrumentation"))
        and bool(rankings.get("genre_style"))
        and bool(rankings.get("vocal_character"))
        and bool(rankings.get("acoustic_electronic"))
        and bool(result.get("energy"))
    )
    source_sha_unchanged = before_sha == after_sha == LOCKED_SHA256 and (
        ingest_before is None or ingest_before == ingest_after == LOCKED_SHA256
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": source_sha_unchanged,
        "protected_artifacts_unchanged": snapshots_match(protected_before, protected_after),
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "download_required": not bool((result.get("checkpoint_state") or {}).get("local_files_only")),
        "analysis_seconds": analysis_seconds,
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "audio_intelligence_run.json")

    print(json.dumps(run_payload, indent=2))
    print(f"AUDIO INTELLIGENCE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not source_sha_unchanged:
        print("FAIL: source SHA changed")
        return 1
    if not snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if not ok:
        print("FAIL: incomplete audio intelligence output")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
