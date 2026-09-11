# ACI-A2L-012 evidence

NVIDIA Parakeet TDT 0.6B v2 wired into the existing A2L operator workflow as an **alternate** engine. Faster-whisper remains primary. Parakeet lyrics were **not** approved.

- Application (this workstation, Parakeet venv): http://127.0.0.1:8781/
- Engine selector on Upload: FASTER-WHISPER / LARGE-V3 (default) or NVIDIA PARAKEET / TDT-0.6B-V2
- Runtime chain: `artifacts/ingest/<sha>/a2l_pipeline_parakeet/` (gitignored)
- `parakeet_workflow_lyrics.txt` — machine draft from the locked Jay master, not approved
- `run.json` — SHA checks, transcription time, lyric state

Locked source SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged. Primary faster-whisper draft, approved lyrics, and whisper-1 hashes unchanged. Transcription 86.21 s on CPU.
