# ACR-A2L-DM-001 — ACI-A2L-DM-001 acceptance

**ACI:** ACI-A2L-DM-001 — Song Object Model  
**Date recorded:** 2026-09-15  
**Branch:** `feature/aci-a2l-dm-001-song-object-model`  
**Base:** `deployable` @ `d5e3c85ed128a8fdc124adaa2dee7c150d3da311`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** documentation / data-model definition only. No registry. No UI. No artifact migration.

Exactly one ACR exists for this ACI.

## Accepted outcome

A2L now has a documented canonical Song Object Model (v1) that sits above existing governed ingest artifacts. `song_id` is defined as distinct from ingest/source identities. Approved Lyrics, SIR, and Song Release Record remain the authorities for their domains. The model references those records, preserves authority/provenance/partial/missing semantics, supports future same-Song multi-master association, and remains compatible with the current product without migration.

SONG OBJECT MODEL DEFINED: PASS  
SONG_ID SEPARATE FROM INGEST/SHA: PASS  
AUTHORITY PRESERVED: PASS  
PROVENANCE PRESERVED: PASS  
MISSING DATA EXPLICIT: PASS  
ARTIFACT MAPPING DOCUMENTED: PASS  
JAY CONCRETE MAPPING: PASS  
MULTI-MASTER RELATIONSHIP DEFINED: PASS  
REGISTRY IMPLEMENTED: NO  
UI CHANGED: NO  
ARTIFACTS MIGRATED: NO  
MASTER HASH UNCHANGED: YES  
RECOMMENDATION: PASS (feature branch; not promoted)

## Evidence (in repo)

- `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md`
- `docs/nebula/data-model/a2l_song_object_model_v1.schema.json`
- `docs/nebula/reports/ACI-A2L-DM-001_COMPLETION_REPORT.md`
- `docs/nebula/aci/ACI-A2L-DM-001.md`

## Gaps

- Song Registry not implemented; `song_id` values are not allocated in product storage.
- Master-revision workflow not implemented beyond the model relationship.
- Album Object / Artist Object remain undefined.
