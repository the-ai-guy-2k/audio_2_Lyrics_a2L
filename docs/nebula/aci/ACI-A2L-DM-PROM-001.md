# ACI-A2L-DM-PROM-001

PROMOTE SONG OBJECT MODEL

AIW: CAE  
STATUS: EXECUTED — PROMOTION TO `deployable`

Permanent copy of the Operator ACI. This execution promotes the validated Song Object Model (ACI-A2L-DM-001) into the formal A2L `deployable` baseline. It adds no new product capability and does not implement a Song Registry.

## Constraints honored

- Source: `feature/aci-a2l-dm-001-song-object-model` @ `72b9024`.
- Implementation commits: `98eac80`, `72b9024`.
- Source baseline / merge-base: `deployable` @ `d5e3c85ed128a8fdc124adaa2dee7c150d3da311` (same as `main` / `origin/deployable` / `origin/main`).
- Promotion docs commit: `0e28126`.
- History-preserving `--no-ff` merge `b51ff20`. No squash. No force-push.
- Final `deployable` / `main` / `origin/deployable` / `origin/main`: `b51ff20667fdce54254dd9a48a8b8e93de199585`.
- Parked/untracked experimental files were not committed.
- Required artifacts after promotion:
  - `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md`
  - `docs/nebula/data-model/a2l_song_object_model_v1.schema.json`
  - `docs/nebula/aci/ACI-A2L-DM-001.md`
  - `docs/nebula/acr/ACR-A2L-DM-001.md`
- `song_id` remains independent of source SHA, ingest_job_id, filename, and analyzer/SIR identity.
- No Song Registry, UI changes, Album/Artist objects, or artifact migration.
- `main` synchronized only because it had no unique/divergent history.

## Explicitly out of scope

DM-002 Song Registry, UI changes, Album Object, Artist Object, unrelated analyzer/runtime repairs, beginning DM-002.
