# ACR-A2L-005 — ACI-A2L-005 acceptance

**ACI:** ACI-A2L-005 — faster-whisper large-v3 transcription test  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-005-faster-whisper-large-v3`  
**Commit:** `b12b7b6`  
**Status:** EXECUTED on feature branch — not merged; lyric quality not accepted by CAE  
**Product changes:** isolated faster-whisper / large-v3 candidate only; whisper-1 pipeline unchanged

## Accepted outcome (execution only)

faster-whisper 1.2.1 with Whisper `large-v3` (`Systran/faster-whisper-large-v3`) transcribed the locked mastered WAV on CPU / int8. Raw JSON and human-readable TXT were stored outside the whisper-1 baseline path. The original master SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. Existing whisper-1 artifacts were not modified. Parakeet was not continued.

CAE does **not** accept lyric quality. Successful model execution is not a quality PASS. Operator reads the transcription.

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-005-faster-whisper-evidence/`
- `scripts/run_faster_whisper_candidate.py`
- `tests/test_faster_whisper_candidate.py`
- `docs/nebula/reports/ACI-A2L-005_COMPLETION_REPORT.md`

## Gaps

- No NVIDIA GPU; CPU int8 used as best available on this workstation.
- Parakeet remains deferred; its experimental branch was not merged into this work.
- This candidate is not wired into the A2L CLI or uncertainty/structuring stages.
