# ACI-A2L-017

MVP BASELINE PROMOTION TO DEPLOYABLE

AIW: CAE  
STATUS: EXECUTED — PROMOTION TO `deployable`

Permanent copy of the Operator ACI. This execution promotes the validated ACI-A2L-016 MVP into the repository's formal `deployable` release baseline. It adds no product capability.

## Constraints honored

- Source: `feature/aci-a2l-016-export-filenames` @ `3937749547503d4ad5264771db3cd09496b2ad94`.
- ACI-A2L-015 Extract-button JavaScript repair (`displayText`) is present in that source and is preserved.
- No new product capability, engines, vocal isolation, LLM correction, cloud deploy, or UI redesign.
- Parked/untracked experimental files were not committed and were not deleted.
- Canonical approved artifacts were not renamed or rewritten.
- ACI-A2L-011 / ACI-A2L-012 ACR rows restored from existing repository evidence only; no invented quality verdicts.
- Root README and operator start docs updated so a normal operator is directed to `.venv-faster-whisper` and http://127.0.0.1:8780/.
- History preserved (no squash of ACI commits).
- `main` assessed before any change. See ACR-A2L-017 for Current Truth and action taken.

## Explicitly out of scope

New features. Cloud infrastructure. Force-push over divergent history. Beginning another feature after promotion.
