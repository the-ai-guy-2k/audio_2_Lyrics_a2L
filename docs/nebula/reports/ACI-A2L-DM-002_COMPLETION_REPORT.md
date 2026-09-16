# ACI-A2L-DM-002 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-DM-002 — Song Registry  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **PASS** (feature branch; not promoted)

---

## Execution status

COMPLETE on `feature/aci-a2l-dm-002-song-registry`. Governed Song Registry implemented against Song Object Model v1. Jay Song registered by reference. UI consumers unchanged. Not promoted.

## Baseline

| Item | Value |
| --- | --- |
| Base `deployable` | `81151fb3599806dfe4b01ab45c0e39e298d44295` |
| Branch | `feature/aci-a2l-dm-002-song-registry` @ `d567260` |
| Registry path | `artifacts/song_registry/song_registry.json` |
| Module | `a2l.song_registry` |

## Validation

| # | Check | Result |
| --- | --- | --- |
| 1 | Song registration works | PASS |
| 2 | Stable song_id created | PASS (`uuid4.hex`, ≠ SHA) |
| 3 | Registry persists across reload | PASS |
| 4 | Enumeration works | PASS |
| 5 | song_id resolves correct Song | PASS |
| 6 | Jay resolves governed artifacts | PASS |
| 7 | Repeat registration no duplicate | PASS |
| 8 | Missing metadata stays missing | PASS |
| 9 | Master SHA unchanged | PASS |
| 10 | Multi-master structure permitted | PASS (`associate_master`) |
| 11 | Existing authority intact | PASS (references only) |
| 12 | Applicable regression run | PASS with known baseline drift distinguished |

Registry tests: `tests/test_song_registry.py` — 6 passed.  
Applicable suite: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py --ignore=tests/test_lyric_engine_runtime.py`  
Result: 205 passed, 2 failed, 1 skipped. Failures are the known locked-Jay artifact-drift tests from the incoming baseline only (`test_locked_song_is_operator_reapproved`, `test_existing_approved_artifact_formats_without_rewrite`). No new DM-002 failures.

Jay registration (workstation):

- `song_id`: `ac8100c8182443a5b690176f48b2ae2c`
- source SHA / ingest: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- approved lyrics / SIR / release refs resolved when present

## Explicitly not done

UI migration, Album/Artist objects, ingest migration, promotion, DM-003, analyzer repairs.

---

## Minority Report

WHAT IS BEING DONE: `song_id` is generated with `uuid4.hex` and indexed by ingest_job_id for idempotency; no fuzzy title/artist matching.  
WHY IT MATTERS: Prevents SHA-as-Song-id collapse and silent duplicate Songs for the same ingest, while refusing autonomous merges of unrelated masters.  
PA IMPACT: NONE for current UI (still ingest-centric).  
DISPOSITION: ACCEPTED

WHAT IS BEING DONE: Distinguishing two known locked-Jay live-artifact regression failures from DM-002 (`test_locked_song_is_operator_reapproved`, `test_existing_approved_artifact_formats_without_rewrite`).  
WHY IT MATTERS: Those failures pre-exist on the incoming baseline from local approved-lyric artifact drift; they are not introduced by the registry.  
PA IMPACT: NONE for Song Registry capability.  
DISPOSITION: INFORMATIONAL
