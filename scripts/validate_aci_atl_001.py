"""ACI-ATL-001 runtime validation against repository behavior."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_wav(path: Path) -> None:
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * 4410)
    path.write_bytes(buffer.getvalue())


def run_ingest(wav_path: Path, artifact_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "a2l",
            "ingest",
            str(wav_path),
            "--artifact-root",
            str(artifact_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    evidence_dir = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-001-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="a2l-aci-atl-001-"))
    try:
        wav_path = work / "control_a.wav"
        artifact_root = work / "artifacts"
        write_wav(wav_path)
        original = wav_path.read_bytes()

        first = run_ingest(wav_path, artifact_root)
        if first.returncode != 0:
            print(first.stderr)
            print("FAIL: valid WAV ingest")
            return 1
        first_payload = json.loads(first.stdout)
        if wav_path.read_bytes() != original:
            print("FAIL: operator source mutated")
            return 1
        if first_payload["source_sha256"] != first_payload["working_sha256"]:
            print("FAIL: working artifact is not byte-identical")
            return 1

        second = run_ingest(wav_path, artifact_root)
        second_payload = json.loads(second.stdout)
        if second.returncode != 0 or first_payload["job_id"] != second_payload["job_id"]:
            print("FAIL: repeat ingest was not deterministic")
            return 1

        invalid = work / "not_audio.txt"
        invalid.write_text("nope", encoding="utf-8")
        invalid_run = run_ingest(invalid, artifact_root)
        if invalid_run.returncode == 0:
            print("FAIL: invalid input was accepted")
            return 1

        corrupt = work / "corrupt.wav"
        corrupt.write_bytes(original[:20])
        corrupt_run = run_ingest(corrupt, artifact_root)
        if corrupt_run.returncode == 0:
            print("FAIL: corrupt WAV was accepted")
            return 1

        evidence = {
            "valid_wav": first_payload,
            "repeat_job_id": second_payload["job_id"],
            "invalid_error": json.loads(invalid_run.stderr),
            "corrupt_error": json.loads(corrupt_run.stderr),
        }
        (evidence_dir / "runtime_validation.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("PASS: ACI-ATL-001 runtime validation")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
