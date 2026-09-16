# ACI-A2L-DM-PROM-002

PROMOTE SONG REGISTRY

AIW: CAE  
STATUS: EXECUTED — PROMOTION TO `deployable`

Permanent copy of the Operator ACI. This execution promotes the validated Song Registry (ACI-A2L-DM-002) into the formal A2L `deployable` baseline. It adds no new Song Registry capability and does not modify product UI consumers.

## Constraints honored

- Source: `feature/aci-a2l-dm-002-song-registry` @ `6a3e1e8`.
- Implementation commits: `d567260`, `6a3e1e8`.
- Source baseline / merge-base: `deployable` @ `81151fb3599806dfe4b01ab45c0e39e298d44295` (same as `main` / `origin/deployable` / `origin/main`).
- Promotion docs commit: `db369c8`.
- History-preserving `--no-ff` merge `fc25981`. No squash. No force-push.
- Parked/untracked experimental files were not committed.
- Required after promotion:
  - `a2l/song_registry.py`
  - `artifacts/song_registry/song_registry.json`
  - Song Object Model v1 + schema + `A2L_SONG_REGISTRY.md`
  - ACI-A2L-DM-002 / ACR-A2L-DM-002
- Jay registration preserved: `song_id` `ac8100c8182443a5b690176f48b2ae2c` → ingest `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.
- No UI consumer changes. No Album/Artist objects. No artifact migration. DM-003 not started.
- `main` synchronized only because it had no unique/divergent history.

## Explicitly out of scope

DM-003, UI migration to registry, Album Object, Artist Object, unrelated analyzer/runtime repairs, new registry capabilities.
