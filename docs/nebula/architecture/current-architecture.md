# A2L current architecture (implemented)

**Authority:** ACI-A2L-009 on `feature/aci-a2l-009-real-song-validation`.

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

No verse/chorus labels. Vocal isolation is not in the pipeline. ACI-A2L-009 Amendment 01: locked song is **REQUIRES_REAPPROVAL** (first approval archived; Operator correction pending).
