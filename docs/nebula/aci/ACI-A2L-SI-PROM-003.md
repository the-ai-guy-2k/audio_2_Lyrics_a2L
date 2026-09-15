# ACI-A2L-SI-PROM-003

PROMOTE GOVERNED SONG INTELLIGENCE RECORD / MVP BASELINE

AIW: CAE  
STATUS: EXECUTED — PROMOTION TO `deployable`

Permanent copy of the Operator ACI. This execution promotes the validated governed Song Intelligence Record (ACI-A2L-SI-012) into the formal A2L `deployable` baseline. It adds no new capability and does not convert MACHINE-DERIVED estimates into human-approved musical facts.

## Constraints honored

- Source: `feature/aci-a2l-si-012-song-intelligence-record` @ `79c8dbd`.
- Implementation commit: `c2f62ba`.
- Source baseline / merge-base: `deployable` @ `bb72ef4156aa7767d913d0864ae8b08420391f14` (same as `main` / `origin/deployable` / `origin/main`).
- History-preserving `--no-ff` merge. No squash. No force-push.
- Parked/untracked experimental files were not committed.
- Instrumentation defect preserved: `docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md` remains open in the bug-fix lane.
- Temporary UI aggregation remains `TEMPORARY_UI_AGGREGATION`, derived, `outranks_sir: false`.
- `main` synchronized only because it had no unique/divergent history.

## Promoted product truth (unchanged)

- Governed SIR: `SONG_INTELLIGENCE_RECORD` schema `1.0.0`
- Default: Full Song Intelligence
- UI consumes the governed SIR
- Vocal Characteristics: PARTIAL
- Instrumentation: PARTIAL
- Audio Intelligence overall: PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD
- Lyric Intelligence requires AUTHORITATIVE APPROVED LYRICS

## Explicitly out of scope

Final SI export, SI human approval, UI redesign, instrumentation repair, threshold/algorithm changes, new engines, chords, mastering QC, source separation as a product, radio, distributor integrations, Jay musical validation.
