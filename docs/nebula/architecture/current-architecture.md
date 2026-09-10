# A2L current architecture (implemented)

**Authority:** ACI-A2L-008 on `feature/aci-a2l-008-approved-lyrics`.

## Implemented flow

```text
Operator WAV (read-only)
  → ingest (CONTROL A)
  → transcribe (faster-whisper / Whisper large-v3; whisper-1 baseline preserved)
  → uncertainty (flag, do not invent)
  → lyric structuring (timed annotated draft, do not rewrite)
  → human review (correct, preserve machine text, save does not approve)
  → explicit human approval (confirm=true)
  → approved lyric artifacts (TXT + JSON)
```

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels. Vocal isolation is not in the pipeline. The locked Jay song remains **NOT APPROVED**.
