# ACR-A2L-SI-010 — ACI-A2L-SI-010 acceptance

**ACI:** ACI-A2L-SI-010 — Instrumentation final resolution  
**Date recorded:** 2026-09-15  
**Branch:** `feature/aci-a2l-si-010-instrumentation-final-resolution`  
**Commit:** `85c67c9`  
**Status:** APPROVED ACI EXECUTED on feature branch — not merged; ENGINE #3 PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD; instrumentation defect deferred to bug-fix lane  
**Product changes:** isolated PANNs instrument-presence candidate only; AST/CLAP not retuned; master WAV unchanged; Song Intelligence Record not created

Exactly one ACR exists for this ACI.

## Accepted outcome (execution only)

ONE specialized instrument-presence candidate was evaluated: PANNs Cnn14 `Cnn14_mAP=0.431.pth` (Zenodo 3987831, CC-BY-4.0). Software is MIT + BSD-style + ISC. CPU sidecar reused `.venv-clap`. GPU and cloud were not required.

Native AudioSet independent clipwise sigmoids on the locked Jay master (21 × 10s chunks):

- Guitar mean=0.1705 max=0.7221
- Plucked string instrument mean=0.1311 max=0.6417
- Electric guitar mean=0.0433 max=0.3206
- Drum kit mean=0.0190
- Synthesizer mean=0.0006

Precommitted operating point 0.50 → strong_count=0. Engineering result: **PARTIAL**, not WIN. AST 0.15 was not changed. AST was not rerun.

ENGINE #3 FINAL RESULT: PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD  
Known defect: `docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md`  
Repair budget: EXHAUSTED. No SI-011 instrumentation repair.

MASTER HASH UNCHANGED: YES  
CPU: PASS  
GPU REQUIRED: NO  
CLOUD REQUIRED: NO  
COMMERCIAL LICENSE GATE: PASS  
MUSICAL VALIDATION: PENDING JAY  
ACI-A2L-SI-010: EXECUTED (not merged)

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-si-010-evidence/`
- `docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md`
- `scripts/run_instrument_presence_candidate.py`
- `tests/test_instrument_presence_candidate.py`
- `docs/nebula/reports/ACI-A2L-SI-010_COMPLETION_REPORT.md`

## Gaps / minority

See structured minority reports in the completion report. Guitar clipwise_max 0.7221 in some 10s windows was not converted into a WIN; song-level score remained clipwise_mean as precommitted.
