# ACI-A2L-SI-008 evidence

Isolated CLAP classification-resolution diagnostic on the locked Jay master. CONTROL is the SI-007 method. RESOLUTION is selected by cosine `top_margin`, not preferred labels. Energy / Intensity was not reopened. SI-007 evidence was not modified.

- `classification_resolution_raw.json` — all methods, templates, text-embedding pairwise stats, rankings
- `classification_resolution_readable.txt` — CONTROL vs RESOLUTION per category
- `classification_resolution_run.json` — SHA, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/clap-classification-resolution/<sha>/` (gitignored).

Checkpoint reused: `laion/larger_clap_music` revision `a0b4534a14f58e20944452dff00a22a06ce629d1`.

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **172 passed**.
