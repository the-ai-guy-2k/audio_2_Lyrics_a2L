# ACR-A2L-DM-PROM-001 — ACI-A2L-DM-PROM-001 acceptance

**ACI:** ACI-A2L-DM-PROM-001 — Promote Song Object Model  
**Date recorded:** 2026-09-15  
**Branch:** `feature/aci-a2l-dm-prom-001`  
**Commit:** `0e28126` (docs); promotion merge `b51ff20` on `deployable`  
**Source tip:** `feature/aci-a2l-dm-001-song-object-model` @ `72b9024`  
**Status:** COMPLETE — promoted to `deployable`  
**Product changes:** none beyond DM-001 documentation/model. Promotion only. No Song Registry.

Exactly one ACR exists for this ACI.

## Accepted outcome

The A2L Song Object Model v1 is part of the formal `deployable` baseline. Machine-readable schema, ACI-A2L-DM-001, and ACR-A2L-DM-001 are present. `song_id` remains independent of source SHA / ingest_job_id / filename / analyzer/SIR identity. No Song Registry, UI, Album/Artist objects, or artifact migration were introduced by this promotion.

SONG OBJECT MODEL IN DEPLOYABLE: PASS  
SCHEMA PRESENT: PASS  
ACI ↔ ACR TRACEABILITY: PASS  
SONG_ID INDEPENDENT: PASS  
SONG REGISTRY INTRODUCED: NO  
UI CHANGED: NO  
ALBUM/ARTIST OBJECT INTRODUCED: NO  
ARTIFACTS MIGRATED: NO  
REGRESSION: promotion delta is docs-only (`a2l/` unchanged). Applicable suite excluding parked Parakeet/BUG-001 files: 199 passed, 2 failed, 1 skipped. The 2 failures are live locked-Jay artifact assertions (`approval_event.revision` expected 2 / observed 1; export header vs canonical txt) from local ingest state, not from this promotion.  
FINAL DEPLOYABLE: `b51ff20667fdce54254dd9a48a8b8e93de199585`  
RECOMMENDATION: PASS

## Evidence (in repo)

- `docs/nebula/aci/ACI-A2L-DM-PROM-001.md`
- `docs/nebula/reports/ACI-A2L-DM-PROM-001_COMPLETION_REPORT.md`
- `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md`
- Source: `feature/aci-a2l-dm-001-song-object-model` @ `72b9024`
- `deployable` / `main` / `origin/deployable` / `origin/main` @ `b51ff20`

## Gaps

- Song Registry remains a later capability (DM-002).
- No `song_id` values are allocated in product storage until a registry exists.
- Locked-Jay live-artifact test expectations may need Operator refresh of revision-2 approved lyrics on this workstation (out of promotion scope).
