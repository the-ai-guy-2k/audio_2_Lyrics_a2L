"""ACI-ATL-004 runtime validation: ingest → transcribe → uncertainty → structure."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PATH = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-003-evidence" / "fixed_song_identity.json"
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-004-evidence"


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

    artifact_root = ROOT / "artifacts"
    ingest = run_cli(["ingest", str(song), "--artifact-root", str(artifact_root)])
    if ingest.returncode != 0:
        print(ingest.stderr)
        print("FAIL: ingest")
        return 1
    ingest_payload = json.loads(ingest.stdout)
    job_dir = Path(ingest_payload["manifest_path"]).parent
    draft_path = job_dir / "machine_transcription" / "transcription_draft.json"
    report_path = job_dir / "uncertainty" / "uncertainty_report.json"

    if not draft_path.is_file():
        transcribe = run_cli(["transcribe", ingest_payload["manifest_path"]])
        if transcribe.returncode != 0:
            print(transcribe.stderr)
            print("FAIL: transcribe")
            return 1
        transcribe_payload = json.loads(transcribe.stdout)
        draft_path = Path(transcribe_payload["draft_path"])
    else:
        transcribe_payload = {"draft_path": str(draft_path), "reused_existing": True}

    if not report_path.is_file():
        uncertainty = run_cli(["uncertainty", str(draft_path)])
        if uncertainty.returncode != 0:
            print(uncertainty.stderr)
            print("FAIL: uncertainty")
            return 1
        uncertainty_payload = json.loads(uncertainty.stdout)
        report_path = Path(uncertainty_payload["report_path"])
    else:
        uncertainty = run_cli(["uncertainty", str(draft_path)])
        if uncertainty.returncode != 0:
            print(uncertainty.stderr)
            print("FAIL: uncertainty")
            return 1
        uncertainty_payload = json.loads(uncertainty.stdout)
        report_path = Path(uncertainty_payload["report_path"])

    structure = run_cli(["structure", str(report_path)])
    if structure.returncode != 0:
        print(structure.stderr)
        print("FAIL: structure")
        return 1
    structure_payload = json.loads(structure.stdout)

    if sha256_file(song) != before_hash or song.stat().st_mtime_ns != before_mtime:
        print("FAIL: original master was modified")
        return 1
    if structure_payload["usable_as_approved_lyrics"] is True:
        print("FAIL: structured draft treated as approved lyrics")
        return 1
    if structure_payload["section_labels_assigned"] is True:
        print("FAIL: verse/chorus labels were invented")
        return 1

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    copy_json(Path(ingest_payload["manifest_path"]), EVIDENCE_DIR / "ingest_manifest.json")
    copy_json(draft_path, EVIDENCE_DIR / "transcription_draft.json")
    copy_json(report_path, EVIDENCE_DIR / "uncertainty_report.json")
    copy_json(Path(structure_payload["draft_path"]), EVIDENCE_DIR / "structured_lyric_draft.json")
    copy_json(Path(structure_payload["text_path"]), EVIDENCE_DIR / "structured_lyric_draft.txt")

    structured = json.loads((EVIDENCE_DIR / "structured_lyric_draft.json").read_text(encoding="utf-8"))
    report = json.loads((EVIDENCE_DIR / "uncertainty_report.json").read_text(encoding="utf-8"))
    machine_texts = [line["preserved_text"] for line in structured["lines"] if line["kind"] == "machine_line"]
    report_texts = [item["preserved_text"] for item in report["items"]]
    if machine_texts != report_texts:
        print("FAIL: structured lines do not preserve uncertainty item text")
        return 1
    if structured["preserved_engine_text"] != report["preserved_engine_text"]:
        print("FAIL: engine text was rewritten")
        return 1

    evidence = {
        "ok": True,
        "real_mastered_song": True,
        "transcription_accuracy_claimed": False,
        "identity": identity,
        "original_master_unchanged": True,
        "ingest": {"job_id": ingest_payload["job_id"], "audio": ingest_payload["audio"]},
        "transcription": transcribe_payload,
        "uncertainty": {
            "job_status": uncertainty_payload["job_status"],
            "counts": uncertainty_payload["counts"],
        },
        "structure": {
            "authority": structure_payload["authority"],
            "approval_status": structure_payload["approval_status"],
            "usable_as_approved_lyrics": structure_payload["usable_as_approved_lyrics"],
            "section_labels_assigned": structure_payload["section_labels_assigned"],
            "counts": structure_payload["counts"],
        },
    }
    (EVIDENCE_DIR / "runtime_validation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: ACI-ATL-004 runtime validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
