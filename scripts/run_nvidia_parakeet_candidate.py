"""ACI-A2L-011 isolated NVIDIA NeMo / Parakeet candidate transcription.

Runs NVIDIA Parakeet TDT 0.6B v2 against the locked mastered WAV.
Does not modify the primary faster-whisper path or overwrite its artifacts.
Does not isolate vocals or send text to an LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
LOCKED_SOURCE = Path(
    r"C:\Users\tim\Desktop\Jays_stuff\2026_album\Masters - 24bit_48hz"
    r"\Masters  - 24bit_48hz\01Stomp to MIX MSTR 24bit_48hz.wav"
)
PARAKEET_MODEL = "nvidia/parakeet-tdt-0.6b-v2"
DEFAULT_NEMO_FILE = Path.home() / ".cache" / "a2l-parakeet" / "parakeet-tdt-0.6b-v2.nemo"
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIR_NAME = "nvidia-parakeet"
WHISPER1_DIR_NAME = "machine_transcription"
PIPELINE_DIR_NAME = "a2l_pipeline"
FASTER_WHISPER_DIR_NAME = "faster-whisper-large-v3"
PARKED_PARAKEET_DIR_NAME = "parakeet"


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
        return [jsonable(v) for v in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return jsonable(value.item())
        except Exception:
            pass
    text = getattr(value, "text", None)
    timestamp = getattr(value, "timestamp", None)
    if text is not None or timestamp is not None:
        return {
            "text": jsonable(text),
            "timestamp": jsonable(timestamp),
            "type": type(value).__name__,
        }
    return repr(value)


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
        "cpu_count": os.cpu_count(),
        "machine": platform.machine(),
        "torch": torch_version,
        "torch_cuda_available": cuda_available,
        "torch_cuda_device": cuda_name,
        "device": "cuda" if cuda_available else "cpu",
        "nvidia_smi": "not_found_on_path",
        "notes": (
            "No NVIDIA GPU/driver is visible. Parakeet is forced to CPU. "
            "Graphics adapter on this workstation is Intel Iris Xe."
        ),
    }


def package_versions() -> dict:
    names = [
        "nemo_toolkit",
        "nemo",
        "torch",
        "torchaudio",
        "lightning",
        "pytorch_lightning",
        "omegaconf",
        "hydra-core",
        "librosa",
        "soundfile",
        "numpy",
        "huggingface_hub",
        "sentencepiece",
        "lhotse",
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
        job / WHISPER1_DIR_NAME,
        job / PIPELINE_DIR_NAME,
        job / "authoritative_source",
        job / "derived_working",
        ROOT / "artifacts" / "candidates" / FASTER_WHISPER_DIR_NAME / sha,
        ROOT / "artifacts" / "candidates" / PARKED_PARAKEET_DIR_NAME / sha,
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


def write_readable_txt(path: Path, text: str, meta: dict) -> None:
    header = [
        "NVIDIA PARAKEET MACHINE TRANSCRIPTION",
        "CANDIDATE ONLY — NON_AUTHORITATIVE_MACHINE_DRAFT",
        "NOT APPROVED LYRICS",
        "Not the A2L primary engine. No LLM repair was applied.",
        f"engine: {meta.get('engine')}",
        f"model: {meta.get('model')}",
        f"nemo: {meta.get('nemo_version')}",
        f"device: {meta.get('device')}",
        f"source_sha256: {meta.get('source_sha256')}",
        "",
        "----- BEGIN ACTUAL MACHINE TEXT -----",
        "",
    ]
    path.write_text("\n".join(header) + (text or "") + "\n", encoding="utf-8")


def transcribe(
    source: Path,
    model_name: str,
    nemo_file: Path | None,
) -> tuple[str, object, list[str], float, str, float, bool, str]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import nemo.collections.asr as nemo_asr
    import torch

    captured: list[str] = []
    timestamps_used = True
    local = nemo_file if nemo_file and nemo_file.is_file() else None
    if local is None and DEFAULT_NEMO_FILE.is_file():
        local = DEFAULT_NEMO_FILE
    if local is None:
        raise FileNotFoundError(
            f"Local Parakeet checkpoint not found: {DEFAULT_NEMO_FILE}. "
            "Refusing HuggingFace download in this run."
        )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        device = torch.device("cpu" if not torch.cuda.is_available() else "cuda")
        load_started = time.perf_counter()
        captured.append(f"loading local checkpoint: {local}")
        asr_model = nemo_asr.models.ASRModel.restore_from(
            restore_path=str(local),
            map_location=device,
        )
        asr_model.eval()
        asr_model = asr_model.to(device)
        load_elapsed = time.perf_counter() - load_started
        started = time.perf_counter()
        # Stereo mastered WAV is (batch, channels, time). EncDecRNNTBPEModel requires (batch, time).
        # channel_selector='average' mixes L/R in memory. This is not vocal isolation.
        # use_lhotse=False: the Lhotse path ignored channel_selector and fed stereo audio.
        # Model cfg sample_rate is 16 kHz; NeMo resamples in memory. Original file is not rewritten.
        captured.append(
            "channel_selector=average (in-memory stereo mixdown; original WAV unchanged; not vocal isolation)"
        )
        captured.append("use_lhotse=False so channel_selector is applied")
        try:
            output = asr_model.transcribe(
                [str(source)],
                timestamps=True,
                channel_selector="average",
                use_lhotse=False,
                batch_size=1,
                num_workers=0,
            )
        except Exception as exc:
            if "Input shape mismatch" in str(exc):
                raise
            timestamps_used = False
            captured.append(f"timestamps=True failed ({type(exc).__name__}: {exc}); retrying without timestamps")
            output = asr_model.transcribe(
                [str(source)],
                timestamps=False,
                channel_selector="average",
                use_lhotse=False,
                batch_size=1,
                num_workers=0,
            )
        elapsed = time.perf_counter() - started
        for item in caught:
            captured.append(warnings.formatwarning(item.message, item.category, item.filename, item.lineno))
    hypothesis = output[0] if output else None
    text = ""
    if hypothesis is not None:
        text = getattr(hypothesis, "text", None) or str(hypothesis)
    return text, hypothesis, captured, elapsed, str(device), load_elapsed, timestamps_used, str(local)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-011 NVIDIA Parakeet candidate")
    parser.add_argument("--source", type=Path, default=LOCKED_SOURCE)
    parser.add_argument("--model", default=PARAKEET_MODEL)
    parser.add_argument("--nemo-file", type=Path, default=DEFAULT_NEMO_FILE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/nvidia-parakeet/<sha256>/",
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

    protected_before = snapshot_protected(LOCKED_SHA256)
    out_dir = args.output_dir or (ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / LOCKED_SHA256)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "nvidia_parakeet_raw.json"
    txt_path = out_dir / "nvidia_parakeet_lyrics.txt"
    run_path = out_dir / "nvidia_parakeet_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, LOCKED_SHA256)

    versions = package_versions()
    hw = hardware_record()
    errors = []
    warning_lines: list[str] = []
    text = ""
    hypothesis = None
    elapsed = None
    load_elapsed = None
    timestamps_used = False
    checkpoint = str(args.nemo_file)
    device = hw["device"]
    started_utc = datetime.now(timezone.utc).isoformat()
    try:
        text, hypothesis, warning_lines, elapsed, device, load_elapsed, timestamps_used, checkpoint = transcribe(
            source, args.model, args.nemo_file
        )
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    after_sha = sha256_file(source)
    protected_after = snapshot_protected(LOCKED_SHA256)
    protected_unchanged = protected_before == protected_after

    nemo_version = versions.get("nemo_toolkit") or versions.get("nemo")
    raw_payload = {
        "candidate": "ACI-A2L-011",
        "engine": "NVIDIA NeMo Speech / Parakeet",
        "model": args.model,
        "checkpoint": checkpoint,
        "nemo_version": nemo_version,
        "usable_as_approved_lyrics": False,
        "approval_status": "NOT_APPROVED",
        "primary_engine_replaced": False,
        "llm_repair_applied": False,
        "vocal_isolation": False,
        "source_path": str(source),
        "source_sha256_before": before_sha,
        "source_sha256_after": after_sha,
        "source_bytes": source.stat().st_size,
        "device": device,
        "processing_seconds": elapsed,
        "model_load_seconds": load_elapsed,
        "timestamps_requested": True,
        "timestamps_used": timestamps_used,
        "audio_input": str(source),
        "audio_resampled_on_disk": False,
        "channel_selector": "average",
        "use_lhotse": False,
        "preprocessing_note": (
            "NVIDIA EncDecRNNTBPEModel requires mono (batch, time). The locked master is "
            "stereo 24-bit/48 kHz. Channels were averaged in memory. NeMo resamples to 16 kHz "
            "in memory. The original recording was not modified. This is not vocal isolation."
        ),
        "package_versions": versions,
        "hardware": hw,
        "warnings": warning_lines,
        "errors": errors,
        "text": text,
    }
    try:
        raw_payload["hypothesis"] = jsonable(hypothesis)
    except Exception as exc:
        raw_payload["hypothesis"] = {"serialize_error": f"{type(exc).__name__}: {exc}"}
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        text,
        {
            "engine": "NVIDIA NeMo Speech / Parakeet",
            "model": args.model,
            "nemo_version": nemo_version,
            "device": device,
            "source_sha256": after_sha,
        },
    )

    evidence_dir = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-011-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, evidence_dir / "nvidia_parakeet_raw.json")
    shutil.copy2(txt_path, evidence_dir / "nvidia_parakeet_lyrics.txt")

    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not errors and bool(text),
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "source_sha_unchanged": before_sha == after_sha == LOCKED_SHA256,
        "protected_artifacts_intact": protected_unchanged,
        "errors": errors,
        "processing_seconds": elapsed,
        "model_load_seconds": load_elapsed,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, evidence_dir / "nvidia_parakeet_run.json")

    print(json.dumps(run_payload, indent=2))
    print("NVIDIA PARAKEET READABLE OUTPUT:")
    print(str(txt_path.resolve()))
    if errors:
        return 1
    if after_sha != LOCKED_SHA256:
        print("FAIL: source SHA changed")
        return 1
    if not protected_unchanged:
        print("FAIL: protected A2L artifacts changed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
