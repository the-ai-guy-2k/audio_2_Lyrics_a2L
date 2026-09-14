# ACR-A2L-SI-004 — ACI-A2L-SI-004 acceptance

**ACI:** ACI-A2L-SI-004 — Key + Mode engine candidate validation  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-si-004-key-mode`  
**Commit:** `fae5a3d`  
**Status:** EXECUTED on feature branch — not merged; ENGINE WIN pending Operator  
**Product changes:** isolated Key + Mode candidate only; lyric/release authority unchanged; Song Intelligence Record not created; chords not estimated

## Accepted outcome (execution only)

librosa `chroma_cqt` with Krumhansl–Schmuckler / Krumhansl–Kessler template correlation analyzed the locked Jay master on CPU from the finished mix. Key A, mode major, supporting confidence 0.0356, correlation score 0.7641. Source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. Dedicated GPU and cloud were not required. Essentia and madmom neural key were not adopted.

CAE does **not** accept musical usefulness. ENGINE WIN is Operator review.

LOCKED MASTER: PASS  
SOURCE HASH UNCHANGED: YES  
CPU EXECUTION: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
SOURCE SEPARATION INVOKED: NO  
OUTPUT AUTHORITY: MACHINE-DERIVED  
OPERATOR REVIEW REQUIRED: YES  
REGRESSION: 145 passed  
ENGINE WIN: PENDING OPERATOR  
ACI-A2L-SI-004: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-004-evidence/`
- `scripts/run_key_mode_candidate.py`
- `tests/test_key_mode_candidate.py`
- `docs/nebula/reports/ACI-A2L-SI-004_COMPLETION_REPORT.md`

## Gaps

- Whole-mix mean chroma; no chord estimate; confidence is a margin/spread score, not a calibrated probability.
- Not wired into the operator application. No Song Intelligence Record.
