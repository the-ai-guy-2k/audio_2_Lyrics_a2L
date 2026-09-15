# ACR-A2L-DM-002 — ACI-A2L-DM-002 acceptance

**ACI:** ACI-A2L-DM-002 — Song Registry  
**Date recorded:** 2026-09-15  
**Branch:** `feature/aci-a2l-dm-002-song-registry`  
**Base:** `deployable` @ `81151fb3599806dfe4b01ab45c0e39e298d44295`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** Song Registry module + persistent index; no UI consumer changes.

Exactly one ACR exists for this ACI.

## Accepted outcome

A2L can register Songs with opaque `song_id` values, enumerate them, resolve them, and map existing governed ingest artifacts by reference. Repeated registration of the same ingest association returns the same `song_id`. The locked Jay ingest is registered and resolves approved lyrics, SIR, release, and master references. Multi-master association is supported on one `song_id`. Authority of existing artifacts is unchanged.

SONG REGISTRATION: PASS  
STABLE SONG_ID: PASS  
PERSISTENCE: PASS  
ENUMERATION: PASS  
RESOLUTION: PASS  
JAY ARTIFACT MAPPING: PASS  
IDEMPOTENCY: PASS  
MISSING METADATA PRESERVED: PASS  
MASTER SHA UNCHANGED: PASS  
MULTI-MASTER STRUCTURE: PASS  
UI MODIFIED: NO  
REGISTRY PROMOTED: NO  
RECOMMENDATION: PASS (feature branch; not promoted)

## Evidence (in repo)

- `a2l/song_registry.py`
- `tests/test_song_registry.py`
- `artifacts/song_registry/song_registry.json`
- `docs/nebula/data-model/A2L_SONG_REGISTRY.md`
- `docs/nebula/reports/ACI-A2L-DM-002_COMPLETION_REPORT.md`

## Gaps

- Operator UI still enumerates ingest jobs, not registry Songs.
- Album relationships remain empty pending Album Object work.
- Full master-revision product workflow is not implemented.
