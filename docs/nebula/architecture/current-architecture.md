# A2L current architecture (implemented)

**Authority:** ACI-ATL-001 on `feature/aci-atl-001`. This is current truth for the empty-repo bootstrap plus ingestion capability.

## Runtime stack

- Python 3.11+
- Standard library `wave` for WAV parse/validation
- CLI: `python -m a2l ingest`
- No ffmpeg, librosa, Demucs, Whisper, or network services

## Implemented flow

```text
Operator WAV (read-only)
  → a2l.wav.validate_wav_bytes
  → SHA-256 job id
  → artifacts/ingest/<sha256>/authoritative_source/source.wav
  → artifacts/ingest/<sha256>/derived_working/transcription_ready.wav
  → artifacts/ingest/<sha256>/ingest_manifest.json
```

Authoritative source and derived working are distinct paths. Working audio is untreated CONTROL A (byte-identical copy). Vocal isolation is not part of this architecture.

## Not implemented

- Transcription / lyric generation / lyric correction
- Vocal isolation / stem separation
- CONTROL B (normalized audio)
- CONTROL C (isolated vocal stem)
- UI
- Production deployment
