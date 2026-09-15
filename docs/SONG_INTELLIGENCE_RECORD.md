# Song Intelligence Record (ACI-A2L-SI-012)

One governed record representing the current Song Intelligence A2L has produced for a governed song.

The record is truth about **what A2L knows**. It does not make every contained value an authoritative musical fact. Example: the record may authoritatively state that the key analyzer estimated A major. That does not make “A major” human-approved.

## Where it lives

```text
artifacts/ingest/<ingest-job-id>/song_intelligence_record.json
```

Prior current records are archived at:

```text
artifacts/ingest/<ingest-job-id>/song_intelligence_record_history/r<n>.json
```

Record type: `SONG_INTELLIGENCE_RECORD`  
Schema version: `1.0.0`

The master WAV stays at `authoritative_source/source.wav`. It is referenced by SHA-256. It is not copied into the record.

## Authority

| Class | Meaning |
| --- | --- |
| AUTHORITATIVE INPUT | Operator-entered identity or approved lyrics used as input |
| MEASURED | Direct measurement (duration, lexical counts, RMS) |
| MACHINE-DERIVED | Analyzer output; not a human-approved song fact |
| HUMAN-APPROVED / AUTHORITATIVE | Existing approved lyrics only |
| MISSING | Value was not supplied; not inferred |

MACHINE-DERIVED is never auto-promoted to HUMAN-APPROVED. PARTIAL is never auto-promoted to WIN.

## Run states

NOT RUN is not failure. MISSING is not zero. PARTIAL is not complete.

If a later analysis does not rerun a category that already has a governed result, that section is kept with `result_origin: REUSED`.

## Temporary UI aggregation

`artifacts/ingest/<job>/song_intelligence_ui/ui_aggregation.json` remains `TEMPORARY_UI_AGGREGATION`. It is a derived cache. It does not outrank the SIR.

## Out of scope

Song Intelligence human approval, final SI PDF/report/export, instrumentation repair, new engines.
