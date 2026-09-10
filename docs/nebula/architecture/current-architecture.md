# A2L current architecture (implemented)

**Authority:** ACI-ATL-004 on `feature/aci-atl-004`.

## Implemented flow

```text
Operator WAV (read-only)
  → ingest (CONTROL A)
  → transcribe (machine draft)
  → uncertainty (flag, do not invent)
  → lyric structuring (timed annotated draft, do not rewrite)
```

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels. No approved lyrics. Vocal isolation is not in the pipeline.
