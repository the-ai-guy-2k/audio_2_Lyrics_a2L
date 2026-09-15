# ACI-A2L-DM-001

SONG OBJECT MODEL

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution defines and documents the canonical A2L Song Object Model. It does not implement a Song Registry, migrate artifacts, change the UI, or alter lyric/SIR/release authority.

## Constraints honored

- Branch `feature/aci-a2l-dm-001-song-object-model` from actual `deployable` / `main` tip `d5e3c85ed128a8fdc124adaa2dee7c150d3da311` (post ACI-A2L-SI-PROM-003). Do not assume older tips.
- Canonical model: `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md`
- Optional machine-readable schema: `docs/nebula/data-model/a2l_song_object_model_v1.schema.json`
- `song_id` defined as opaque Song identity, separate from ingest job id, source SHA-256, filename, and SIR revision
- Same Song may associate multiple master revisions; master-replacement workflow not implemented
- Song resolves references to Approved Lyrics, SIR, Song Release Record, and Album membership without competing copies
- Authority / provenance / partial / missing semantics preserved from existing governed artifacts
- Concrete mapping validated against locked Jay ingest job `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` without modifying those artifacts
- `deployable` and `main` not modified. Not promoted.

## Explicitly out of scope

Song Registry implementation, Album Object, Artist Object, UI changes, ingest migration, analyzer changes or repairs, lyric authority changes, SIR authority changes, release behavior changes, promotion.
