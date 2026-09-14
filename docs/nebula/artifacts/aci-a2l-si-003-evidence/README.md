# ACI-A2L-SI-003 evidence

Diagnostic All-In-One mixed-audio structure path on the locked Jay master. MACHINE-DERIVED. HTDemucs is analyzer plumbing only, not an A2L product capability. SI-002 rhythm evidence was not rewritten.

- `structure_raw.json` — raw machine artifact
- `structure_readable.txt` — human-readable timestamped sections
- `structure_run.json` — SHA, CPU/GPU/cloud, diagnostic separation, timing, memory

Runtime copies: `artifacts/candidates/all-in-one-infer/<sha>/si-003-structure-resolution/` (gitignored).

Investigation:
- A: no mix-only Harmonix path (K=4 stem spectrograms required)
- B: mix-as-stems already failed; no remaining config without fabricating stems
- C: not started; Engine #1 structure was diagnosed via official mixed path

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **139 passed** (Python 3.14.3).
