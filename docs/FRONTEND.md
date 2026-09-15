# A2L application frontend (ACI-A2L-010)

The operator application coordinates the validated A2L pipeline. It does not replace transcription, review, or approval rules.

This is the **product-facing** path: **http://127.0.0.1:8780/**

The engineering review interface at http://127.0.0.1:8765/ (`python -m a2l review`) is a separate page. Operators start the application, not the engineering review UI.

## Start

Primary supported local start (faster-whisper / Whisper large-v3 extract):

```bash
.venv-faster-whisper\Scripts\python.exe -m a2l app
```

Open http://127.0.0.1:8780/

Established procedure: [OPERATOR_START.md](OPERATOR_START.md)

`python -m a2l app` on default Python 3.14 starts the UI only. It cannot run faster-whisper extraction on this workstation.

NVIDIA Parakeet / TDT-0.6B-V2 is an **alternate** engine in a separate `.venv-parakeet`. It is not primary.

## Workflow

Upload → optional Song title / Artist → Extract lyrics → Review / correct → Approve → Output → Release record → Album manifest → Release Readiness → Release package export → Song Intelligence

- Upload uses existing WAV ingest. The original recording is not modified.
- Song title and artist are optional. The file name is not used as the title. Missing values are not invented.
- Extract uses ingest → selected engine (default faster-whisper / Whisper large-v3, or NVIDIA Parakeet) → uncertainty → structuring.
- Review keeps paragraph lyrics, uncertainty marks, Save (not approval), and reopen/reapproval. Title and artist can be corrected before approval.
- After approval, Output shows STANDARD LYRIC SHEET by default, including any supplied title/artist. The operator may select PLAIN TEXT or STRUCTURED LYRICS, then preview, copy, or download that presentation. Download filenames use Artist and Song Title when supplied (ACI-A2L-016); the WAV file name is not used.
- Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain the authoritative files. Formatted files are derived.
- **Release** collects song-level release Current Truth (credits, rights, ISRC if entered). Missing fields stay MISSING. READY is record completeness, not commercial release. See [SONG_RELEASE_RECORD.md](SONG_RELEASE_RECORD.md).
- **Album** aggregates existing Song Release Records into one Operator-ordered album view. Missing per-song fields stay visible. See [ALBUM_RELEASE_MANIFEST.md](ALBUM_RELEASE_MANIFEST.md).
- **Release Readiness** on Album reports A2L INTERNAL RELEASE READINESS (READY or INCOMPLETE). READY is internal completeness, not distributor or commercial release. See [ALBUM_RELEASE_READINESS.md](ALBUM_RELEASE_READINESS.md).
- **Export release package** on Album writes a portable ZIP of current governed album/song artifacts. READY and INCOMPLETE albums may both export. Master audio is not copied. See [RELEASE_PACKAGE_EXPORT.md](RELEASE_PACKAGE_EXPORT.md).
- **Song Intelligence** analyzes a governed song with Full Song Intelligence as the default. Advanced engine selection is optional. After analysis the UI reads the governed Song Intelligence Record. See [SONG_INTELLIGENCE_RECORD.md](SONG_INTELLIGENCE_RECORD.md) and [SONG_INTELLIGENCE_UI.md](SONG_INTELLIGENCE_UI.md).

Internal paths, SHAs, and engine details stay off the screen.
