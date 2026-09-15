# ACI-A2L-SI-002 evidence

Isolated All-In-One / `all-in-one-infer` 3.1.0 rhythm + structure candidate. MACHINE-DERIVED. Not a Song Intelligence Record. Not written into approved lyrics or release authority.

- `all_in_one_raw.json` — raw machine artifact (versions, hardware, probes, BPM, beats, downbeats, segments)
- `all_in_one_readable.txt` — human-readable machine output
- `all_in_one_run.json` — SHA verification, CPU/GPU/cloud/separation flags, timing, memory

Runtime copies also exist under `artifacts/candidates/all-in-one-infer/<sha256>/` (gitignored).

Mix-first path: finished master presented as bass/drums/other/vocals (`mix-as-stems`). HTDemucs was not invoked. Official mixed-audio `analyze()` would invoke HTDemucs and was not run.

24-bit master could not be mmap-read by madmom-infer. A derived 32-bit PCM working copy was used. Authoritative source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.

Sidecar: `.venv-all-in-one` (Python 3.12.10). Not installed into Python 3.14 A2L.

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **135 passed** (Python 3.14.3).
