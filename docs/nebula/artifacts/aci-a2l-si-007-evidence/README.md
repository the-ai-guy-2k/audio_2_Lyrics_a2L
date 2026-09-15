# ACI-A2L-SI-007 evidence

Isolated LAION CLAP Audio Intelligence on the locked Jay master. Master WAV is AUTHORITATIVE INPUT. CLAP rankings are MACHINE-DERIVED cosine similarities, not calibrated probabilities. Energy RMS/onset values are MEASURED; HIGH/MEDIUM/LOW ENERGY is MACHINE-DERIVED. No Song Intelligence Record.

- `audio_intelligence_raw.json` — raw machine artifact, vocabularies, prompts, scores
- `audio_intelligence_readable.txt` — ranked instrumentation, genre, vocal, acoustic/electronic, energy
- `audio_intelligence_run.json` — SHA, CPU/GPU/cloud, timing, memory

Runtime copies: `artifacts/candidates/clap-audio-intelligence/<sha>/` (gitignored).

Checkpoint: `laion/larger_clap_music` revision `a0b4534a14f58e20944452dff00a22a06ce629d1` (Apache-2.0). Incomplete SI-005 snapshot weights were discarded; the complete local blob (776,444,665 bytes, SHA-256 `5c289311…`) was reused. Text embeddings use EOS-token projection (LAION convention). Hugging Face `ClapTextPooler` was not used.

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **165 passed** (Python 3.14.3; 153 SI-006 baseline + 12 SI-007 isolation tests).
