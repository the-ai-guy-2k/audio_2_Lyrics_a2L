# A2L current architecture (implemented)

**Authority:** ACI-A2L-006 on `feature/aci-a2l-006-human-review`.

## Implemented flow

```text
Operator WAV (read-only)
  → ingest (CONTROL A)
  → transcribe (faster-whisper large-v3 for review; whisper-1 baseline preserved)
  → uncertainty (flag, do not invent)
  → lyric structuring (timed annotated draft, do not rewrite)
  → human review (correct, preserve machine text, not approved)
```

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels. No approved lyrics. Vocal isolation is not in the pipeline.
