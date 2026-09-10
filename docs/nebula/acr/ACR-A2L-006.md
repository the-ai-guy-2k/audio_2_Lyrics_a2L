# ACR-A2L-006 — ACI-A2L-006 acceptance

**ACI:** ACI-A2L-006 — Human review and correction  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-006-human-review`  
**Commit:** implementation commit on this branch (recorded after first commit)  
**Status:** COMPLETE on feature branch — not merged; lyrics not approved  
**Product changes:** local review UI; machine vs human text preserved; reviewed draft saved

## Accepted outcome

The locked song structured draft from faster-whisper large-v3 can be reviewed. Uncertainty is visible. Line 36 machine text `Hunkers with that old school funk` was corrected to `Hook us with that old school funk`. Reload kept the correction. Original machine text remains on the same line. `usable_as_approved_lyrics` remains false.

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-006-evidence/`
- `tests/test_review.py`
- `docs/HUMAN_REVIEW.md`
- `docs/REVIEW_CONTRACT.md`
- `docs/nebula/reports/ACI-A2L-006_COMPLETION_REPORT.md`

## Gaps

- Review is a local stdlib HTTP page, not a polished product UI.
- The one locked-song correction is a capability proof, not a full lyric pass.
