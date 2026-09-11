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

Upload → optional Song title / Artist → Extract lyrics → Review / correct → Approve → Output

- Upload uses existing WAV ingest. The original recording is not modified.
- Song title and artist are optional. The file name is not used as the title. Missing values are not invented.
- Extract uses ingest → selected engine (default faster-whisper / Whisper large-v3, or NVIDIA Parakeet) → uncertainty → structuring.
- Review keeps paragraph lyrics, uncertainty marks, Save (not approval), and reopen/reapproval. Title and artist can be corrected before approval.
- After approval, Output shows STANDARD LYRIC SHEET by default, including any supplied title/artist. The operator may select PLAIN TEXT or STRUCTURED LYRICS, then preview, copy, or download that presentation. Download filenames use Artist and Song Title when supplied (ACI-A2L-016); the WAV file name is not used.
- Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain the authoritative files. Formatted files are derived.

Internal paths, SHAs, and engine details stay off the screen.
