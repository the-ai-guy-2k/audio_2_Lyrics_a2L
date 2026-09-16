# ACR-A2L-DM-PROM-002 — ACI-A2L-DM-PROM-002 acceptance

**ACI:** ACI-A2L-DM-PROM-002 — Promote Song Registry  
**Date recorded:** 2026-09-15  
**Branch:** `feature/aci-a2l-dm-prom-002`  
**Source tip:** `feature/aci-a2l-dm-002-song-registry` @ `6a3e1e8`  
**Status:** COMPLETE — promoted to `deployable`  
**Product changes:** none beyond DM-002. Promotion of the validated Song Registry only. No UI consumer changes.

Exactly one ACR exists for this ACI.

## Accepted outcome

The Song Registry is part of the formal `deployable` baseline. Persistent registry, opaque `song_id`, ingest idempotency, multi-master association, and Jay mapping by reference are present. Approved Lyrics, SIR, and Song Release Record remain authoritative via references. Product UI consumers are unchanged. Known locked-Jay live-artifact drift remains an inherited baseline condition, not a promotion regression.

SONG REGISTRY IN DEPLOYABLE: PASS  
PERSISTENCE / REGISTER / LIST / GET: PASS  
JAY SONG_ID PRESERVED: PASS  
AUTHORITY BY REFERENCE: PASS  
UI MODIFIED: NO  
NEW REGISTRY CAPABILITY ADDED DURING PROMOTION: NO  
RECOMMENDATION: PASS

## Evidence (in repo)

- `docs/nebula/aci/ACI-A2L-DM-PROM-002.md`
- `docs/nebula/reports/ACI-A2L-DM-PROM-002_COMPLETION_REPORT.md`
- `a2l/song_registry.py`
- `artifacts/song_registry/song_registry.json`
- Source: `feature/aci-a2l-dm-002-song-registry` @ `6a3e1e8`

## Gaps

- Operator UI still enumerates ingest jobs, not registry Songs (deferred).
- Album relationships remain empty pending Album Object work.
