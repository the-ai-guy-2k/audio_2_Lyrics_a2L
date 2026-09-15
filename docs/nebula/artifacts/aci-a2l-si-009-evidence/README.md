# ACI-A2L-SI-009 evidence

Isolated AST AudioSet music-tagging candidate on the locked Jay master. Master WAV is AUTHORITATIVE INPUT. Native AST tags are MACHINE-DERIVED sigmoid scores, not calibrated probabilities. CLAP was not rerun or replaced. No Song Intelligence Record.

- `instrumentation_genre_raw.json` — native 527-class scores, instrument/genre subsets, groups, SI-008 comparison
- `instrumentation_genre_readable.txt` — ranked native instrumentation and genre/style
- `instrumentation_genre_run.json` — SHA, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/ast-instrumentation-genre/<sha>/` (gitignored).

Checkpoint: `MIT/ast-finetuned-audioset-10-10-0.4593` revision `f826b80d28226b62986cc218e5cec390b1096902` (BSD-3-Clause). Sidecar reused `.venv-clap`. Cache: `%USERPROFILE%\.cache\a2l-ast`.

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **181 passed**.
