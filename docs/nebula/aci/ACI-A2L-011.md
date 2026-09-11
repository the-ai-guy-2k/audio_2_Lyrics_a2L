# ACI-A2L-011

NVIDIA TRANSCRIPTION ENGINE CANDIDATE EVALUATION

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — AWAITING OPERATOR QUALITY REVIEW

Permanent copy of the Operator ACI. This execution evaluates NVIDIA NeMo / Parakeet TDT 0.6B v2 on the locked mastered song. It does not replace the primary faster-whisper / Whisper large-v3 engine.

## Constraints honored

- New branch `feature/aci-a2l-011-nvidia-candidate` from `feature/aci-a2l-010-frontend`.
- Parked ACI-A2L-005 Parakeet files were not silently committed or reused as the primary path.
- Same locked WAV: `01Stomp to MIX MSTR 24bit_48hz.wav`
- SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- Candidate artifacts under `artifacts/candidates/nvidia-parakeet/<sha>/`
- Primary `a2l_pipeline`, approved lyrics, whisper-1, Operator corrections, and faster-whisper candidate artifacts are not overwritten.
- No vocal isolation.
- No LLM repair/rewrite.
- Not merged. Not pushed. Not promoted.

## Explicitly out of scope

Primary-engine replacement, frontend redesign, approval workflow changes, automatic lyric correction, unrelated A2L features.
