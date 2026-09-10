# ACI-A2L-005 faster-whisper large-v3 evidence

Isolated faster-whisper large-v3 candidate output. Does **not** replace the whisper-1 baseline under `artifacts/ingest/<sha>/machine_transcription/`. Does **not** write into Parakeet paths.

- `faster_whisper_large_v3_raw.json` — raw machine artifact (versions, hardware, decoding, actual text/segments)
- `faster_whisper_large_v3_lyrics.txt` — human-readable machine transcription
- `faster_whisper_large_v3_run.json` — SHA verification and preservation checks

Runtime copies also exist under `artifacts/candidates/faster-whisper-large-v3/<sha256>/` (gitignored).
