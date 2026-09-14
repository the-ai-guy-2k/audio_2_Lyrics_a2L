# ACI-A2L-SI-006 evidence

Isolated deterministic lyric intelligence on the locked Jay approved lyrics (revision 2). Approved lyrics are AUTHORITATIVE INPUT. Themes, emotion, subject, and synopsis are MACHINE-DERIVED. Lexical counts are MEASURED. Audio was not transcribed. No Song Intelligence Record.

- `lyric_intelligence_raw.json` — raw machine artifact
- `lyric_intelligence_readable.txt` — human-readable themes, keywords, emotion, subject, synopsis
- `lyric_intelligence_run.json` — approved-hash, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/lyric-intelligence/<sha>/` (gitignored).

Engine #3 / CLAP was not resumed. Incomplete `pytorch_model.bin` transfer was not restarted. Network stop rule was not triggered for Engine #4 (no download required).

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py --ignore=tests/test_audio_intelligence_candidate.py` — **153 passed** (Python 3.14.3; 145 SI-004 baseline + 8 SI-006 isolation tests).
