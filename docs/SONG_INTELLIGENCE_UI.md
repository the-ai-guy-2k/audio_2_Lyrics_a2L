# Song Intelligence product UI (ACI-A2L-SI-011)

Operator application (product-facing): http://127.0.0.1:8780/ → **Song Intelligence**

This screen orchestrates the promoted Song Intelligence analyzers and shows results in one human-readable view. It is **not** the governed Song Intelligence Record. It does not approve Song Intelligence. It does not change approved lyric authority.

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
| MEASURED | Direct measurement (duration, RMS, onsets) |
| MACHINE-DERIVED | Analyzer output; not a human-approved song fact |
| HUMAN-APPROVED / AUTHORITATIVE | Existing approved lyrics only |

Vocal characteristics and instrumentation remain **Partial**. They are not shown as authoritative facts.

Lyric Intelligence requires **AUTHORITATIVE APPROVED LYRICS**. Unapproved transcription is not substituted.

## Temporary aggregation

If a file is written for display, it lives at `artifacts/ingest/<job>/song_intelligence_ui/ui_aggregation.json`.

Kind: `TEMPORARY_UI_AGGREGATION`. It is derived, non-authoritative, and is not a Song Intelligence Record.

## Out of scope

Governed Song Intelligence Record, Song Intelligence approval, instrumentation repair, chords, mastering QC, source separation as a product, distributor integrations.
