# Song Intelligence product UI (ACI-A2L-SI-011 / ACI-A2L-SI-012)

Operator application (product-facing): http://127.0.0.1:8780/ → **Song Intelligence**

This screen orchestrates the promoted Song Intelligence analyzers. After analysis it displays the current governed Song Intelligence Record. It does not approve Song Intelligence. It does not change approved lyric authority.

See [SONG_INTELLIGENCE_RECORD.md](SONG_INTELLIGENCE_RECORD.md).

## Default path

1. Choose a governed A2L song.
2. Keep **Full Song Intelligence**.
3. Click **Analyze song**.
4. Read results by group: Song, Lyrics, Music, Sound, Meaning, Provenance / Authority.

Advanced engine selection is optional and closed by default. It can only narrow the selected analysis. It does not invent extra engines.

## Authority

| Kind | Meaning |
| --- | --- |
| AUTHORITATIVE INPUT | Operator-entered song identity or approved lyrics used as input |
| MEASURED | Direct measurement (duration, RMS, onsets, lexical counts) |
| MACHINE-DERIVED | Analyzer output; not a human-approved song fact |
| HUMAN-APPROVED / AUTHORITATIVE | Existing approved lyrics only |

Vocal characteristics and instrumentation remain **Partial**. They are not shown as authoritative facts.

Lyric Intelligence requires **AUTHORITATIVE APPROVED LYRICS**. Unapproved transcription is not substituted.

## Governed record vs temporary aggregation

Governed record: `artifacts/ingest/<job>/song_intelligence_record.json` (`SONG_INTELLIGENCE_RECORD`).

Derived cache: `artifacts/ingest/<job>/song_intelligence_ui/ui_aggregation.json` (`TEMPORARY_UI_AGGREGATION`). It does not outrank the SIR.

## Out of scope

Song Intelligence approval, instrumentation repair, chords, mastering QC, source separation as a product, distributor integrations, final SI export.
