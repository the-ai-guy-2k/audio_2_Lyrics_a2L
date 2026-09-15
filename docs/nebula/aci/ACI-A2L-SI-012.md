# ACI-A2L-SI-012

GOVERNED SONG INTELLIGENCE RECORD

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution creates one governed Song Intelligence Record per analyzed song. It combines existing validated Song Intelligence results without collapsing provenance, authority, validation state, or partial status. It does not promote those values to human-approved musical facts.

## Constraints honored

- Branch `feature/aci-a2l-si-012-song-intelligence-record` from `deployable` / `main` @ `bb72ef4156aa7767d913d0864ae8b08420391f14`.
- Implementation commit: `c2f62ba`.
- Record path: `artifacts/ingest/<job>/song_intelligence_record.json`.
- Record type: `SONG_INTELLIGENCE_RECORD`. Schema version: `1.0.0`.
- Temporary UI aggregation remains `TEMPORARY_UI_AGGREGATION` at `song_intelligence_ui/ui_aggregation.json`. It is a derived cache and does not outrank the SIR.
- The operator UI consumes the SIR after analysis. Input/output controls were not redesigned.
- Instrumentation remains PARTIAL and deferred. Defect file unchanged in disposition.
- Missing title/artist stay MISSING. Filename is not used as title.
- Selective analysis records NOT RUN. Repeated generation archives the prior revision.
- Master WAV is referenced, not copied.
- No Song Intelligence human approval. No final SI export.
- `deployable` and `main` were not modified. Not promoted.

## Explicitly out of scope

Instrumentation repair, new engines, threshold/algorithm changes, chords, mastering QC, source separation as a product, Jay musical validation, SI approval workflow, final SI PDF/report/export, radio, distributor integrations, promotion.
