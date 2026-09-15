# ACI-A2L-DM-002

SONG REGISTRY

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution implements the governed Song Registry that operationalizes Song Object Model v1. It does not modify operator UI consumers, migrate ingest storage, or promote.

## Constraints honored

- Branch `feature/aci-a2l-dm-002-song-registry` from `deployable` @ `81151fb3599806dfe4b01ab45c0e39e298d44295`.
- Implementation commit: `d567260`.
- Model authority: `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md` and schema.
- Persistent registry: `artifacts/song_registry/song_registry.json`.
- Module API: `register_song`, `list_songs`, `get_song`, `associate_master`.
- `song_id` is opaque `uuid4.hex`, not source SHA / ingest_job_id / filename / SIR id.
- Jay locked ingest mapped; artifacts referenced, not copied.
- Idempotent registration by ingest association.
- Multi-master association supported without changing `song_id`.
- No UI changes. No Album/Artist objects. Not promoted.

## Explicitly out of scope

UI consumer migration, Album Object, Artist Object, ingest migration, promotion, DM-003, unrelated analyzer/runtime repairs.
