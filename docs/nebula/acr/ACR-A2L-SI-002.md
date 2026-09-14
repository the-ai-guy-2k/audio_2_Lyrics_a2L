# ACR-A2L-SI-002 — ACI-A2L-SI-002 acceptance

**ACI:** ACI-A2L-SI-002 — Rhythm + Structure engine candidate validation  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-si-002-rhythm-structure`  
**Commit:** pending implementation SHA  
**Status:** EXECUTED on feature branch — not merged; ENGINE WIN pending Operator  
**Product changes:** isolated All-In-One candidate only; lyric/release authority unchanged; Song Intelligence Record not created

## Accepted outcome (execution only)

`all-in-one-infer` 3.1.0 with `harmonix-all` analyzed the locked Jay master on CPU using mix-as-stems. HTDemucs was not invoked. BPM 98, 298 beats, 74 downbeats, and timestamped sections were captured. Source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. Dedicated GPU and cloud were not required.

CAE does **not** accept musical usefulness. ENGINE WIN is Operator review.

LOCKED MASTER: PASS  
SOURCE HASH UNCHANGED: YES  
CPU EXECUTION: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
SOURCE SEPARATION INVOKED: NO  
OUTPUT AUTHORITY: MACHINE-DERIVED  
OPERATOR REVIEW REQUIRED: YES  
REGRESSION: 135 passed  
ENGINE WIN: PENDING OPERATOR  
ACI-A2L-SI-002: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-002-evidence/`
- `scripts/run_all_in_one_candidate.py`
- `tests/test_all_in_one_candidate.py`
- `docs/nebula/reports/ACI-A2L-SI-002_COMPLETION_REPORT.md`

## Gaps

- Official mixed-audio All-In-One still internally uses HTDemucs. That path was not run and is not accepted A2L design.
- Mix-as-stems structure is chorus-dominated; Operator must judge whether that is useful.
- 24-bit masters require a derived wider-PCM working copy for madmom-infer mmap.
- Not wired into the operator application. No Song Intelligence Record.
