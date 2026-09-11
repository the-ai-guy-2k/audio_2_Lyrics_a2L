# ACR-A2L-017 — ACI-A2L-017 acceptance

**ACI:** ACI-A2L-017 — MVP baseline promotion to deployable  
**Date recorded:** 2026-09-11  
**Branch:** `feature/aci-a2l-017-mvp-baseline-promotion`  
**Commit:** `a197bf5`  
**Status:** COMPLETE — promoted to `deployable` (merge SHA recorded on `deployable` after this ACR)  
**Product changes:** none. Documentation, traceability restoration, and release-branch promotion only.

## Accepted outcome

The validated ACI-A2L-016 MVP (104 tests, Extract-button repair preserved) is the formal `deployable` baseline. README and operator docs point to `.venv-faster-whisper` and http://127.0.0.1:8780/. ACI-A2L-011 and ACI-A2L-012 ACR rows exist from existing evidence without invented quality verdicts. Parked experimental files were not committed.

SOURCE BASELINE: `feature/aci-a2l-016-export-filenames` @ `3937749`  
PRODUCT CAPABILITY ADDED: NO  
README / OPERATOR DOCS: CURRENT  
ACI-011 / ACI-012 TRACEABILITY: COMPLETE (restored from existing evidence; 011 has no completion report)  
PARKED FILES COMMITTED: NO  
RECOMMENDATION: PASS

## Evidence (in repo)

- `README.md`
- `docs/OPERATOR_START.md`
- `docs/nebula/acr/ACR-A2L-011.md`
- `docs/nebula/acr/ACR-A2L-012.md`
- `docs/nebula/reports/ACI-A2L-017_COMPLETION_REPORT.md`

## Gaps

- `gh` is not authenticated on this workstation. Remote push uses git credentials if available.
- No original 011 completion report exists; ACR-A2L-011 records that gap.
- Default Python 3.14 still cannot extract with faster-whisper; that is documented, not a promotion defect.
