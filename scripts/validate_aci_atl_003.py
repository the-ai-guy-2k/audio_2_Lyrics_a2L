"""ACI-ATL-003 runtime validation: ingest → transcribe → uncertainty on the fixed song."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PATH = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-003-evidence" / "fixed_song_identity.json"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-003-evidence"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "a2l", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def copy_json(src: Path, dest: Path) -> None:
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    song = Path(identity["source_path"])
    if not song.is_file():
        print(f"FAIL: fixed song missing: {song}")
        return 1
    before_hash = sha256_file(song)
    if before_hash != identity["sha256"]:
        print("FAIL: fixed song SHA-256 does not match locked identity")
        return 1
    before_mtime = song.stat().st_mtime_ns
    before_size = song.stat().st_size

    artifact_root = ROOT / "artifacts"
    ingest = run_cli(["ingest", str(song), "--artifact-root", str(artifact_root)])
    if ingest.returncode != 0:
        print(ingest.stderr)
        print("FAIL: ingest")
        return 1
    ingest_payload = json.loads(ingest.stdout)
    if sha256_file(song) != before_hash or song.stat().st_mtime_ns != before_mtime:
        print("FAIL: original master was modified")
        return 1

    transcribe = run_cli(["transcribe", ingest_payload["manifest_path"]])
    if transcribe.returncode != 0:
        print(transcribe.stderr)
        print("FAIL: transcribe")
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "runtime_validation.json").write_text(
            json.dumps(
                {
                    "ok": False,
                    "stage": "transcribe",
                    "identity": identity,
                    "ingest": ingest_payload,
                    "transcribe_error": transcribe.stderr,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1
    transcribe_payload = json.loads(transcribe.stdout)

    uncertainty = run_cli(["uncertainty", transcribe_payload["draft_path"]])
    if uncertainty.returncode != 0:
        print(uncertainty.stderr)
        print("FAIL: uncertainty")
        return 1
    uncertainty_payload = json.loads(uncertainty.stdout)

    if sha256_file(song) != before_hash or song.stat().st_mtime_ns != before_mtime:
        print("FAIL: original master was modified after pipeline")
        return 1
    if uncertainty_payload["usable_as_approved_lyrics"] is True:
        print("FAIL: uncertainty promoted lyrics")
        return 1

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    copy_json(Path(ingest_payload["manifest_path"]), EVIDENCE_DIR / "ingest_manifest.json")
    copy_json(Path(transcribe_payload["draft_path"]), EVIDENCE_DIR / "transcription_draft.json")
    copy_json(Path(uncertainty_payload["report_path"]), EVIDENCE_DIR / "uncertainty_report.json")

    draft = json.loads((EVIDENCE_DIR / "transcription_draft.json").read_text(encoding="utf-8"))
    report = json.loads((EVIDENCE_DIR / "uncertainty_report.json").read_text(encoding="utf-8"))
    evidence = {
        "ok": True,
        "real_mastered_song": True,
        "transcription_accuracy_claimed": False,
        "identity": identity,
        "original_master_unchanged": {
            "sha256": before_hash,
            "byte_size": before_size,
            "mtime_ns": before_mtime,
        },
        "ingest": {
            "job_id": ingest_payload["job_id"],
            "audio": ingest_payload["audio"],
            "control_baseline": ingest_payload["control_baseline"],
        },
        "transcription": {
            "engine": transcribe_payload["engine"],
            "flags": transcribe_payload["flags"],
            "approval_status": transcribe_payload["approval_status"],
            "engine_text_length": len(draft.get("engine_text") or ""),
        },
        "uncertainty": {
            "job_status": uncertainty_payload["job_status"],
            "flags": uncertainty_payload["flags"],
            "counts": uncertainty_payload["counts"],
            "established_lyrics_present": uncertainty_payload["established_lyrics_present"],
            "resolution_required": uncertainty_payload["resolution_required"],
        },
        "material_observations": {
            "chunked_upload": draft.get("engine", {}).get("configuration", {}).get("chunked_upload"),
            "chunk_count": draft.get("engine", {}).get("configuration", {}).get("chunk_count"),
            "sample_width_bytes": ingest_payload["audio"]["sample_width_bytes"],
            "uncertainty_job_status": report.get("job_status"),
        },
    }
    (EVIDENCE_DIR / "runtime_validation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: ACI-ATL-003 runtime validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
