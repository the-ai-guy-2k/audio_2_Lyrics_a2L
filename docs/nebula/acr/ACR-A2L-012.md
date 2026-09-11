# ACR-A2L-012 — ACI-A2L-012 acceptance

**ACI:** ACI-A2L-012 — NVIDIA Parakeet A2L workflow integration  
**Date recorded:** 2026-09-11 (traceability restored from existing repository evidence; execution recorded 2026-09-10)  
**Branch:** `feature/aci-a2l-012-nvidia-workflow`  
**Commit:** `7de3466`  
**Status:** EXECUTED on feature branch — alternate engine; not promoted; Parakeet lyrics not approved  
**Product changes:** Parakeet selectable as an alternate transcription engine in the existing operator workflow.

## Accepted outcome (from existing evidence)

NVIDIA Parakeet / TDT-0.6B-V2 was connected to the existing A2L workflow as a functional **alternate** engine. Faster-whisper / Whisper large-v3 remains primary. Parakeet writes `a2l_pipeline_parakeet/`. Primary `a2l_pipeline` and locked Jay approved lyrics were not overwritten. CAE did not approve Parakeet lyrics and did not decide an engine quality winner.

PARAKEET ALTERNATE ENGINE: AVAILABLE  
PRIMARY ENGINE: faster-whisper / Whisper large-v3  
PROMOTED TO PRIMARY: NO  
PARAKEET LYRICS APPROVED: NO

## Evidence (in repo; not invented)

- `docs/nebula/aci/ACI-A2L-012.md`
- `docs/nebula/reports/ACI-A2L-012_COMPLETION_REPORT.md`
- `docs/nebula/artifacts/aci-a2l-012-evidence/README.md`
- `a2l/engines.py` / operator engine selector
- `tests/test_parakeet_workflow.py`
- Implementation commit `7de3466`

## Gaps

- No original ACR was written at execution time; this record restores ACI↔ACR linkage from the completion report and evidence already in the repository.
- Parakeet remains alternate. Isolated parked 005 candidate helpers remain untracked and are not this ACR.
