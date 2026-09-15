# ACR-A2L-SI-007 — ACI-A2L-SI-007 acceptance

**ACI:** ACI-A2L-SI-007 — Audio Intelligence engine candidate validation  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-si-007-audio-intelligence`  
**Commit:** `f1e7125`  
**Status:** APPROVED ACI EXECUTED on feature branch — not merged; PASS; ENGINEERING WIN yes; MUSICAL VALIDATION pending Jay  
**Product changes:** isolated Audio Intelligence candidate only; master WAV and approved lyrics unchanged; Song Intelligence Record not created

Exactly one ACR exists for this ACI.

## Accepted outcome (execution only)

Hugging Face `transformers` `ClapModel` with `laion/larger_clap_music` revision `a0b4534a14f58e20944452dff00a22a06ce629d1` (Apache-2.0) ranked bounded instrumentation, genre/style, vocal, and acoustic/electronic labels on CPU from the locked finished mix. Energy used librosa RMS and onset density (MEASURED) with a MACHINE-DERIVED HIGH/MEDIUM/LOW label. Source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. GPU and cloud were not required. Incomplete prior snapshot weights were not treated as valid.

CAE does **not** accept musical usefulness. MUSICAL VALIDATION is Jay review.

MASTER INPUT: PASS  
MASTER SHA-256 UNCHANGED: YES  
CPU EXECUTION: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
DOWNLOAD: no new CLAP weights; complete local blob reused  
OUTPUT AUTHORITY: AUTHORITATIVE INPUT / MEASURED / MACHINE-DERIVED as classified  
OPERATOR REVIEW REQUIRED: YES  
REGRESSION: 165 passed  
ENGINEERING WIN: YES  
MUSICAL VALIDATION: PENDING JAY  
OUTCOME: PASS  
ACI-A2L-SI-007: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-007-evidence/`
- `scripts/run_audio_intelligence_candidate.py`
- `tests/test_audio_intelligence_candidate.py`
- `docs/nebula/reports/ACI-A2L-SI-007_COMPLETION_REPORT.md`

## Gaps / minority

See structured minority reports in the completion report. Hugging Face first-token text pooler collapsed labels and was replaced with EOS-token projection. Softmax-within-category remains poorly peaked because `logit_scale_a` ≈ 1.03. Vocal male/female scores are a near-tie. Not wired into the operator application. No Song Intelligence Record.
