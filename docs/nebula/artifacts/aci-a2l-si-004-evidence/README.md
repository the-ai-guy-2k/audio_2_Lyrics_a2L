# ACI-A2L-SI-004 evidence

Isolated librosa `chroma_cqt` + Krumhansl–Schmuckler / Krumhansl–Kessler key+mode estimate on the locked Jay master. MACHINE-DERIVED. Chords were not estimated. No Song Intelligence Record.

- `key_mode_raw.json` — raw machine artifact
- `key_mode_readable.txt` — human-readable key, mode, confidence, alternates
- `key_mode_run.json` — SHA, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/key-mode/<sha>/` (gitignored).

Rejected candidates: Essentia KeyExtractor (AGPL/NC), madmom neural key (NC weights).

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **145 passed** (Python 3.14.3; 139 SI-003 baseline + 6 SI-004 isolation tests).
