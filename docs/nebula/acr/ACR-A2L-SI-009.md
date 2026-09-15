# ACR-A2L-SI-009 — ACI-A2L-SI-009 acceptance

**ACI:** ACI-A2L-SI-009 — Instrumentation & genre resolution candidate  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-si-009-instrumentation-genre-resolution`  
**Commit:** pending implementation commit  
**Status:** APPROVED ACI EXECUTED on feature branch — not merged; ENGINE #3 PARTIAL PASS; MUSICAL VALIDATION pending Jay  
**Product changes:** isolated AST instrumentation/genre candidate only; CLAP not replaced; master WAV unchanged; Song Intelligence Record not created

Exactly one ACR exists for this ACI.

## Accepted outcome (execution only)

ONE specialized candidate was evaluated: Hugging Face `transformers` `ASTForAudioClassification` with `MIT/ast-finetuned-audioset-10-10-0.4593` revision `f826b80d28226b62986cc218e5cec390b1096902`. Checkpoint license is BSD-3-Clause (Hugging Face card + original AST repo). Software licenses are commercially acceptable. CPU sidecar reused `.venv-clap`. GPU and cloud were not required.

Native AudioSet sigmoid scores on the locked Jay master:

- Instrumentation: NO WIN (Guitar 0.0654 vs Plucked string instrument 0.0512; top_margin=0.0142; strong_count=0)
- Genre / Style: WIN (Grunge 0.1673 vs Independent music 0.1099; top_margin=0.0573; strong_count=1)

ENGINE #3 RESULT: PARTIAL PASS. Energy / Intensity and Acoustic / Electronic remain the SI-007 / SI-008 CLAP WINs and were not reopened. Vocal remains PARTIAL. Instrumentation remains unresolved. Repair Attempt 3 remains available and was not started.

MASTER HASH UNCHANGED: YES  
CPU: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
COMMERCIAL LICENSE GATE: PASS  
MUSICAL VALIDATION: PENDING JAY  
ACI-A2L-SI-009: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-009-evidence/`
- `scripts/run_instrumentation_genre_candidate.py`
- `tests/test_instrumentation_genre_candidate.py`
- `docs/nebula/reports/ACI-A2L-SI-009_COMPLETION_REPORT.md`

## Gaps / minority

See structured minority reports in the completion report. Genre winner is Grunge, not a country-rock label; that is engine truth, not a Jay-approved genre. Instrumentation ranking is guitar-led and more ordered than CLAP, but below precommitted discrimination thresholds.
