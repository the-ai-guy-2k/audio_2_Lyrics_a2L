# ACI-A2L-007 evidence

Primary faster-whisper / Whisper large-v3 transcription path. Historical whisper-1 files under `artifacts/ingest/<sha>/machine_transcription/` were not overwritten.

- `transcription_draft.json` / `.txt` — primary `python -m a2l transcribe` output
- `reviewed_lyric_draft.json` / `.txt` — human review after the locked-song pipeline
- `runtime_validation.json` — engine versions, SHA checks, persistence

Runtime copies: `artifacts/ingest/<sha>/a2l_pipeline/` (gitignored).
