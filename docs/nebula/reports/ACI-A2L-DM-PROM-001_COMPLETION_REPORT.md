# ACI-A2L-DM-PROM-001 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-DM-PROM-001 — Promote Song Object Model  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **PASS**

---

## Execution status

COMPLETE. Validated ACI-A2L-DM-001 Song Object Model promoted into `deployable` by history-preserving `--no-ff` merge. No Song Registry. No UI. No migration. DM-002 not started.

## Baseline

| Item | Value |
| --- | --- |
| Pre-promotion `deployable` / `main` | `d5e3c85ed128a8fdc124adaa2dee7c150d3da311` |
| Source branch | `feature/aci-a2l-dm-001-song-object-model` @ `72b9024` |
| DM-001 commits | `98eac80`, `72b9024` |
| Promotion branch | `feature/aci-a2l-dm-prom-001` @ `0e28126` |
| Promotion merge on `deployable` | `b51ff20667fdce54254dd9a48a8b8e93de199585` |
| Final `deployable` / `main` / origin | `b51ff20667fdce54254dd9a48a8b8e93de199585` |

## Required artifacts confirmed on deployable

- `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md`
- `docs/nebula/data-model/a2l_song_object_model_v1.schema.json`
- `docs/nebula/aci/ACI-A2L-DM-001.md`
- `docs/nebula/acr/ACR-A2L-DM-001.md`

## Validation checklist

| # | Check | Result |
| --- | --- | --- |
| 1 | deployable contains complete DM-001 capability | PASS |
| 2 | Song Object Model documentation present | PASS |
| 3 | machine-readable schema present | PASS |
| 4 | ACI ↔ ACR traceability preserved | PASS |
| 5 | song_id independent of SHA / ingest / filename / SIR | PASS |
| 6 | No Song Registry introduced | PASS |
| 7 | No UI changes introduced | PASS |
| 8 | No Album/Artist Object introduced | PASS |
| 9 | No governed artifacts migrated/rewritten | PASS |
| 10 | Applicable regression PASS | PASS with noted local locked-Jay artifact drift (see Minority Report) |
| 11 | Working tree clean after promotion | PASS for tracked promotion files; parked untracked experimental files remain untracked |
| 12 | Final deployable commit hash | `b51ff20667fdce54254dd9a48a8b8e93de199585` |

Regression command: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py --ignore=tests/test_lyric_engine_runtime.py`  
Result: 199 passed, 2 failed, 1 skipped. Failures: `test_locked_song_is_operator_reapproved` (revision 1 vs expected 2), `test_existing_approved_artifact_formats_without_rewrite` (STANDARD export adds title/artist from local approved JSON while canonical TXT has no header). Promotion changed docs only; `git diff d5e3c85..b51ff20 -- a2l` empty.

## Explicitly not done

DM-002, Song Registry, UI changes, Album/Artist objects, unrelated fixes.

---

## Minority Report

WHAT IS BEING DONE: Recording that two locked-Jay live-artifact tests failed on this workstation after a docs-only promotion.  
WHY IT MATTERS: Operators must not treat those failures as evidence that DM-PROM-001 changed product code. The approved JSON now carries title/artist and `approval_event.revision == 1` while tests still expect Amendment-01 revision 2 shape.  
PA IMPACT: NONE for the promoted model. Local Jay approval artifact refresh is Operator/governed lyric work, not this promotion.  
DISPOSITION: INFORMATIONAL — promotion PASS retained; no unrelated lyric rewrite performed.
