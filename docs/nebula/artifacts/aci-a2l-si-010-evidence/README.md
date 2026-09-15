# ACI-A2L-SI-010 evidence

Isolated PANNs Cnn14 instrument-presence candidate on the locked Jay master. Master WAV is AUTHORITATIVE INPUT. Native PANNs tags are MACHINE-DERIVED independent clipwise sigmoids, not calibrated probabilities. AST was not rerun. AST 0.15 was not changed. No Song Intelligence Record.

- `instrument_presence_raw.json` — native scores, instrument subset, groups, SI-009 comparison
- `instrument_presence_readable.txt` — ranked native instrumentation
- `instrument_presence_run.json` — SHA, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/panns-instrument-presence/<sha>/` (gitignored).

Checkpoint: `Cnn14_mAP=0.431.pth` Zenodo 3987831 (CC-BY-4.0), md5 `541141fa2ee191a88f24a3219fff024e`. Sidecar reused `.venv-clap`. Cache: `%USERPROFILE%\.cache\a2l-panns`.

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **190 passed**.
