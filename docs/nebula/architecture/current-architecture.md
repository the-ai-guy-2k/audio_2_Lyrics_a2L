# A2L current architecture (implemented)

**Authority:** ACI-A2L-010 on `feature/aci-a2l-010-frontend`.

## Implemented flow

```text
Operator application (python -m a2l app → http://127.0.0.1:8780/)
  Upload WAV
  → ingest (CONTROL A)
    → transcribe (faster-whisper / Whisper large-v3; whisper-1 baseline preserved)
    → uncertainty (flag, do not invent)
    → lyric structuring (timed annotated draft, do not rewrite)
    → human review (paragraph lyrics, correct, save does not approve)
    → explicit human approval (confirm=true)
    → export approved_lyrics.txt / approved_lyrics.json
    → optional reopen (archives prior approval) → reapprove
```

The engineering review page remains `python -m a2l review` at http://127.0.0.1:8765/.

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels. Vocal isolation is not in the pipeline. The locked Jay song is **APPROVED** (ACI-A2L-009 Amendment 01, revision 2) and was not modified by ACI-A2L-010.
