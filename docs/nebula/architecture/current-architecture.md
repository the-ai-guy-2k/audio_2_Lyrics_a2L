# A2L current architecture (implemented)

**Authority:** ACI-ATL-002 on `feature/aci-atl-002`, built on ACI-ATL-001 CONTROL-A ingest.

## Runtime stack

- Python 3.11+
- Standard library `wave` for WAV parse/validation and energy checks
- CLI: `python -m a2l ingest` and `python -m a2l transcribe`
- CONTROL-A transcription engine: OpenAI `whisper-1` via Audio Transcriptions API (baseline, not GVCA-locked)
- No ffmpeg, librosa, Demucs, or local Whisper/torch in this product

## Implemented flow

```text
Operator WAV (read-only)
  → a2l.wav.validate_wav_bytes
  → artifacts/ingest/<sha256>/authoritative_source/source.wav
  → artifacts/ingest/<sha256>/derived_working/transcription_ready.wav
  → artifacts/ingest/<sha256>/ingest_manifest.json
        ↓
  a2l.transcribe.transcribe_from_manifest
        ↓
  artifacts/ingest/<sha256>/machine_transcription/transcription_draft.json
```

Authoritative source remains immutable. Working audio remains untreated CONTROL A. Transcription is a non-authoritative machine draft. Vocal isolation is not part of this architecture.

## Not implemented

- Lyric structuring / human approval / approved lyric artifacts
- Vocal isolation / stem separation
- CONTROL B (normalized audio)
- CONTROL C (isolated vocal stem)
- UI
- Production deployment
