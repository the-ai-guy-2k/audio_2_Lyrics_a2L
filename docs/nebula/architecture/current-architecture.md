# A2L current architecture (implemented)

**Authority:** ACI-A2L-016 on `feature/aci-a2l-016-export-filenames`, branched from the ACI-A2L-015 validated MVP.

## Implemented flow

```text
Operator application (python -m a2l app)
  Upload WAV + optional song title / artist (filename is not the title)
    → choose engine BEFORE transcription
      default: faster-whisper / Whisper large-v3  → ingest_job/a2l_pipeline/
      alternate: NVIDIA Parakeet / TDT-0.6B-V2   → ingest_job/a2l_pipeline_parakeet/
  → ingest (CONTROL A)
  → persist operator metadata at ingest_job/song_metadata.json
  → transcribe (selected engine; whisper-1 baseline preserved)
  → uncertainty (flag, do not invent)
  → lyric structuring (timed annotated draft, do not rewrite)
  → human review (paragraph lyrics, optional title/artist correction, save does not approve)
  → explicit human approval (confirm=true)
  → canonical approved_lyrics.txt / approved_lyrics.json (title/artist retained if supplied)
  → derived Output presentations (default: STANDARD LYRIC SHEET uses supplied metadata)
  → user download filename from supplied Artist / Song Title (sanitized; does not rename canonical files)
  → optional reopen (archives prior approval + derived exports) → metadata may be corrected → reapprove
```

The engineering review page remains `python -m a2l review` at http://127.0.0.1:8765/ and continues to default to the primary faster-whisper `a2l_pipeline`.

This workstation's Parakeet-enabled operator app for ACI-A2L-012 review: http://127.0.0.1:8781/

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels are invented. Vocal isolation is not in the pipeline. Song title and artist are operator-supplied and optional; the WAV filename is not used as a title. After approval the operator Output screen shows a Standard Lyric Sheet derived from the approved artifact; canonical TXT/JSON remain authoritative. Downloaded files are named from that metadata when present. The locked Jay song's **faster-whisper** approved lyrics (ACI-A2L-009 Amendment 01, revision 2) were not modified. Parakeet output is a separate unapproved chain.
