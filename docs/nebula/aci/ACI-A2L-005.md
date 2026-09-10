# ACI-A2L-005

FASTER-WHISPER LARGE-V3 TRANSCRIPTION TEST

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — AWAITING OPERATOR QUALITY REVIEW

Permanent copy of the Operator ACI. This execution evaluates faster-whisper with Whisper large-v3 on the locked mastered song. NVIDIA NeMo / Parakeet is deferred and was not continued. Transcription quality is **not** decided by CAE.

## Mission

Evaluate faster-whisper / large-v3 as an alternative transcription engine for A2L. Do not advance any other A2L capability.

## Constraints honored

- New branch `feature/aci-a2l-005-faster-whisper-large-v3` from validated ACI-ATL-004 (`feature/aci-atl-004` @ `35c636f`).
- Did not branch from `feature/aci-a2l-005-parakeet`.
- Existing `feature/aci-atl-004` was not modified or merged.
- Implementation commit: `b12b7b6`.
- Parakeet branch and uncommitted Parakeet files were left uncommitted on this branch.
- Same locked WAV: `01Stomp to MIX MSTR 24bit_48hz.wav`
- SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- whisper-1 baseline preserved; faster-whisper artifacts stored separately.
- Parakeet artifacts were not overwritten.
- No vocal isolation.
- No LLM repair/rewrite/inference.
- Actual machine transcription preserved.
- Not merged. Not pushed.

## Explicitly out of scope

Parakeet, vocal isolation, lyric correction, LLM reconstruction, uncertainty logic, lyric structuring, human review UI, approval workflow, approved lyrics, other transcription candidates.
