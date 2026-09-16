# ACI-A2L-DM-PROM-002 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-DM-PROM-002 — Promote Song Registry  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **PASS**

---

## Execution status

COMPLETE. Validated ACI-A2L-DM-002 Song Registry promoted into `deployable` by history-preserving `--no-ff` merge. No new registry capability. No UI changes. DM-003 not started.

## Baseline

| Item | Value |
| --- | --- |
| Pre-promotion `deployable` / `main` | `81151fb3599806dfe4b01ab45c0e39e298d44295` |
| Source branch | `feature/aci-a2l-dm-002-song-registry` @ `6a3e1e8` |
| DM-002 commits | `d567260`, `6a3e1e8` |
| Promotion branch | `feature/aci-a2l-dm-prom-002` @ `db369c8` |
| Promotion merge on `deployable` | `fc2598125df81cf890dfdf12aa44586f6656d38c` |

## Validation checklist

| # | Check | Result |
| --- | --- | --- |
| 1 | deployable contains complete DM-002 | PASS |
| 2 | Registry persists and loads | PASS |
| 3 | register_song works | PASS |
| 4 | list_songs works | PASS |
| 5 | get_song works | PASS |
| 6 | associate_master remains valid | PASS (unit coverage) |
| 7 | Jay song_id resolves expected ingest | PASS `ac8100c8182443a5b690176f48b2ae2c` → `bbc70025…` |
| 8 | Approved lyrics referenced APPROVED | PASS |
| 9 | SIR referenced | PASS |
| 10 | Release referenced where present | PASS |
| 11 | Idempotency preserved | PASS |
| 12 | song_id independent of SHA/ingest | PASS |
| 13 | Multi-master structure permitted | PASS |
| 14 | Missing metadata stays missing | PASS |
| 15 | Master hash unchanged | PASS |
| 16 | Applicable regression executed | PASS with known drift only |

Regression: `tests/test_song_registry.py` 6 passed.  
`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py --ignore=tests/test_lyric_engine_runtime.py` → 205 passed, 2 failed, 1 skipped. Failures unchanged from incoming baseline locked-Jay drift. No new promotion failures. UI files unchanged (`a2l/app.html`, `a2l/app_server.py`).

## Explicitly not done

DM-003, UI migration, Album/Artist objects, artifact migration, unrelated repairs, new registry features.

---

## Minority Report

WHAT IS BEING DONE: Recording inherited locked-Jay live-artifact drift (2 known failures) as baseline condition if unchanged by this docs/code promotion of DM-002.  
WHY IT MATTERS: Must not be confused with a new promotion regression.  
PA IMPACT: NONE for Song Registry deployability.  
DISPOSITION: INFORMATIONAL
