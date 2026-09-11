# ACI-A2L-012

NVIDIA PARAKEET A2L WORKFLOW INTEGRATION

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — READY FOR PARAKEET A2L WORKFLOW REVIEW

Permanent copy of the Operator ACI. This execution connects the validated NVIDIA Parakeet candidate to the existing A2L lyric workflow as a functional alternate engine. It does not replace faster-whisper as the primary engine.

## Constraints honored

- New branch `feature/aci-a2l-012-nvidia-workflow` from `feature/aci-a2l-011-nvidia-candidate` @ `465438b`.
- Validated candidate unchanged: NVIDIA NeMo Speech / nemo-toolkit 3.0.0 / EncDecRNNTBPEModel / `nvidia/parakeet-tdt-0.6b-v2`.
- Python 3.12.10 `.venv-parakeet`, CPU, in-memory stereo average + 16 kHz resample. Original WAV not rewritten.
- Default engine remains faster-whisper / large-v3.
- Parakeet artifacts under `ingest/<sha>/a2l_pipeline_parakeet/`. Primary `a2l_pipeline`, approved Jay lyrics, whisper-1, and prior Operator corrections were not overwritten.
- Same paragraph review UI. Save is not approval. CAE did not approve Parakeet lyrics.
- No vocal isolation. No LLM lyric correction. Frontend not redesigned.
- Not merged. Not pushed. Not promoted.

## Explicitly out of scope

Promoting Parakeet to primary, removing faster-whisper, vocal isolation, LLM correction, additional engines, altering previously approved lyrics, merge/push.
