# Approved lyric export formatting (ACI-A2L-013)

After explicit approval, A2L presents the approved lyrics as a readable lyric sheet. This does not replace the canonical approved artifacts.

## Authority

```text
AUTHORITATIVE_APPROVED_LYRICS
  approved_lyrics.txt
  approved_lyrics.json
        ↓ derived presentation only
  approved_lyrics/exports/
    lyric-sheet.txt
    lyrics.txt
    structured-lyrics.txt
    export_provenance.json
```

Derived files have authority `DERIVED_EXPORT_PRESENTATION` and `usable_as_approved_lyrics: false`. They are not a substitute for the approved TXT/JSON.

Unapproved lyrics cannot generate these exports.

## Default output

STANDARD LYRIC SHEET. After approval the operator application moves to **Output** and shows that sheet. No format choice is required to see the normal result.

If the approved JSON already has `song_title`/`title` and/or `artist`, those values are shown above the lyrics. Missing metadata is not invented. The WAV filename is not used as a title.

## Format selector

| Choice | What it shows |
| --- | --- |
| STANDARD LYRIC SHEET | Default. Clean lyric layout; optional existing title/artist header |
| PLAIN TEXT | Canonical approved lyric text with no extra presentation |
| STRUCTURED LYRICS | Existing `section_label` values only (Verse / Chorus / Bridge if already stored). Otherwise the same as the canonical text |

Preview, Copy, and Download all use the currently selected format.

## Operator application

Approve → Output.

- Preview: `GET /api/export?format=...`
- Download: `GET /export/output.txt?format=...`
- Canonical artifacts remain at `GET /export/approved_lyrics.txt` and `GET /export/approved_lyrics.json`

Copy uses the text currently shown in the preview.

## Engine independence

Formatting reads the approved artifact. It does not depend on whether the machine draft came from faster-whisper / Whisper large-v3 or NVIDIA Parakeet / TDT-0.6B-V2.
