# A2L current architecture (implemented)

**Authority:** ACI-ATL-003 on `feature/aci-atl-003`, built on ACI-ATL-001 ingest and ACI-ATL-002 CONTROL-A transcription.

## Runtime stack

- Python 3.11+
- Standard library `wave` for WAV parse/validation and energy checks (including 24-bit PCM)
- CLI: `python -m a2l ingest`, `python -m a2l transcribe`, `python -m a2l uncertainty`
- CONTROL-A transcription engine: OpenAI `whisper-1` (baseline, not GVCA-locked)
- Files over the Whisper 25 MB upload limit are sent as temporary same-format PCM slices. Chunks are not stored as working artifacts.
- No Demucs, local Whisper/torch, lyric approval, or vocal isolation

## Implemented flow

```text
Operator WAV (read-only)
  → ingest (CONTROL A)
  → transcribe (machine draft, not approved)
  → uncertainty (flag, do not invent)
```

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

## Not implemented

- Lyric structuring / human approval / approved lyric artifacts
- Vocal isolation / stem separation
- CONTROL B / CONTROL C
- UI / production deployment
