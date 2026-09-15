# ACR-A2L-SI-008 — ACI-A2L-SI-008 acceptance

**ACI:** ACI-A2L-SI-008 — Audio Intelligence classification resolution  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-si-008-audio-classification-resolution`  
**Commit:** `207301f`  
**Status:** APPROVED ACI EXECUTED on feature branch — not merged; ENGINE #3 PARTIAL PASS; MUSICAL VALIDATION pending Jay  
**Product changes:** isolated CLAP classification diagnostic only; SI-007 evidence preserved; master WAV unchanged; Song Intelligence Record not created

Exactly one ACR exists for this ACI.

## Accepted outcome (execution only)

CONTROL reproduced SI-007 cosine rankings. Equivalent richer prompts, a 3-template ensemble, bare labels, and per-window mean cosine were compared. Resolution was selected by `top_margin`, not preferred musical answers.

Category results:

- Instrumentation: NO WIN (ensemble lifted margin 0.0003 → 0.0042; still below 0.008)
- Genre / Style: NO WIN (bare margin 0.0015)
- Vocal Characteristics: PARTIAL (ensemble margin 0.0083)
- Acoustic / Electronic: WIN (CONTROL margin 0.0292; other methods did not beat CONTROL)

ENGINE #3 RESULT: PARTIAL PASS. Energy / Intensity remains the SI-007 WIN and was not reopened. Acoustic/electronic is useful under CONTROL. Instrumentation and genre remain unresolved unique-label classifications.

MASTER HASH UNCHANGED: YES  
CPU: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
ADDITIONAL DOWNLOAD: NO  
SI-007 EVIDENCE UNCHANGED: YES  
MUSICAL VALIDATION: PENDING JAY  
ACI-A2L-SI-008: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-008-evidence/`
- `scripts/run_audio_classification_resolution.py`
- `tests/test_audio_classification_resolution.py`
- `docs/nebula/reports/ACI-A2L-SI-008_COMPLETION_REPORT.md`

## Gaps / minority

See structured minority reports in the completion report. Ensemble instrumentation winner is synthesizer; that is engine truth under the margin rule, not a claim that the mix is synth-led.
