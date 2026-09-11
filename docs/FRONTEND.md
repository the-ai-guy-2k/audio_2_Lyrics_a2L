# A2L application frontend (ACI-A2L-010)

The operator application coordinates the validated A2L pipeline. It does not replace transcription, review, or approval rules.

## Start

```bash
python -m a2l app
```

Open http://127.0.0.1:8780/

On this workstation, real song extraction uses isolated `.venv-faster-whisper` (Python 3.12) so faster-whisper / Whisper large-v3 is available:

```bash
.venv-faster-whisper\Scripts\python.exe -m a2l app
```

The engineering review page remains `python -m a2l review` at http://127.0.0.1:8765/

## Workflow

Upload → Extract lyrics → Review / correct → Approve → Output

- Upload uses existing WAV ingest. The original recording is not modified.
- Extract uses ingest → selected engine (default faster-whisper / Whisper large-v3, or NVIDIA Parakeet) → uncertainty → structuring.
- Review keeps paragraph lyrics, uncertainty marks, Save (not approval), and reopen/reapproval.
- After approval, Output shows STANDARD LYRIC SHEET by default. The operator may select PLAIN TEXT or STRUCTURED LYRICS, then preview, copy, or download that presentation.
- Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain the authoritative files. Formatted files are derived.

Internal paths, SHAs, and engine details stay off the screen.
