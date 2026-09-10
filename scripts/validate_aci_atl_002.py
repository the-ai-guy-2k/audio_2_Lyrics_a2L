"""ACI-ATL-002 runtime validation against repository behavior."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_silence_wav(path: Path) -> None:
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * 4410)
    path.write_bytes(buffer.getvalue())


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "a2l", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    evidence_dir = ROOT / "docs" / "nebula" / "artifacts" / "aci-atl-002-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="a2l-aci-atl-002-"))
    live_error = None
    live_payload = None
    try:
        wav_path = work / "control_a_silence.wav"
        artifact_root = work / "artifacts"
        write_silence_wav(wav_path)
        original = wav_path.read_bytes()

        ingest = run_cli(["ingest", str(wav_path), "--artifact-root", str(artifact_root)])
        if ingest.returncode != 0:
            print(ingest.stderr)
            print("FAIL: ingest required by ACI-ATL-002")
            return 1
        ingest_payload = json.loads(ingest.stdout)
        manifest_path = Path(ingest_payload["manifest_path"])
        source_path = Path(ingest_payload["authoritative_source"])
        working_path = Path(ingest_payload["derived_working"])
        source_bytes = source_path.read_bytes()
        working_bytes = working_path.read_bytes()

        if os.environ.get("OPENAI_API_KEY"):
            live = run_cli(["transcribe", str(manifest_path)])
            if live.returncode == 0:
                live_payload = json.loads(live.stdout)
                draft = json.loads(Path(live_payload["draft_path"]).read_text(encoding="utf-8"))
                if wav_path.read_bytes() != original:
                    print("FAIL: operator source mutated")
                    return 1
                if source_path.read_bytes() != source_bytes or working_path.read_bytes() != working_bytes:
                    print("FAIL: stored audio mutated")
                    return 1
                if draft["usable_as_approved_lyrics"] is True or draft["approval_status"] == "APPROVED":
                    print("FAIL: draft treated as approved lyrics")
                    return 1
                live_payload["draft_flags"] = draft["flags"]
                live_payload["engine_text"] = draft["engine_text"]
                live_payload["signal"] = draft["signal"]
            else:
                try:
                    live_error = json.loads(live.stderr)
                except json.JSONDecodeError:
                    live_error = {"error": live.stderr, "returncode": live.returncode}
        else:
            live_error = {"error_code": "ENGINE_UNAVAILABLE", "error": "OPENAI_API_KEY is not set"}

        evidence = {
            "real_mastered_wav_used": False,
            "real_song_validation": "NOT_CLAIMED",
            "input_consumed": {
                "kind": "generated_pcm_silence_wav",
                "ingest_job_id": ingest_payload["job_id"],
                "manifest_path": ingest_payload["manifest_path"],
                "working_audio": ingest_payload["derived_working"],
                "control_baseline": "CONTROL_A",
            },
            "ingest": ingest_payload,
            "live_transcription": live_payload,
            "live_error": live_error,
        }
        (evidence_dir / "runtime_validation.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if live_payload is None:
            print("PARTIAL: ingest path validated; live Whisper API did not succeed")
            print(json.dumps(live_error, indent=2))
            return 0
        print("PASS: ACI-ATL-002 runtime validation")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
