# ACI-A2L-SI-011

SONG INTELLIGENCE PRODUCT UI

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds the first product-facing Song Intelligence interface inside the existing A2L operator application. It orchestrates promoted analyzers. It does not create the governed Song Intelligence Record.

## Constraints honored

- New branch `feature/aci-a2l-si-011-product-ui` from validated `deployable` @ `f95ed9a807884d44a5b8fbe0be05e051c66058cd`.
- Integrated into http://127.0.0.1:8780/. Engineering review UI on 8765 was not used.
- Default analysis is Full Song Intelligence.
- Capability selection and Advanced engine selection constrain which promoted modules run.
- ANALYZE SONG orchestrates selected analyzers. Isolated candidate scripts are not a required operator step.
- Approved lyrics remain AUTHORITATIVE INPUT for Lyric Intelligence. Unapproved transcription is not substituted.
- Vocal characteristics and instrumentation remain PARTIAL. The instrumentation defect was not reopened or repaired.
- Temporary UI aggregation is derived and non-authoritative. No governed Song Intelligence Record was created.
- No Song Intelligence approval action.
- `deployable` and `main` were not modified. Not merged. Not promoted.

## Explicitly out of scope

Instrumentation repair, SI-012 / governed Song Intelligence Record, Song Intelligence approval workflow, chords, mastering QC, source separation as a product, distributor integrations, Jay musical validation, promotion.
