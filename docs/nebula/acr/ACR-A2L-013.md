# ACR-A2L-013 — ACI-A2L-013 acceptance

**ACI:** ACI-A2L-013 — Approved lyric export formatting  
**Date recorded:** 2026-09-11  
**Branch:** `feature/aci-a2l-013-approved-export-formatting`  
**Commit:** `18bcd53`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** derived Standard Lyric Sheet after approval; format selector; copy/download of selected presentation.

## Accepted outcome

After explicit approval, the operator application shows STANDARD LYRIC SHEET by default. The operator can select PLAIN TEXT or STRUCTURED LYRICS without changing approved lyric words. Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain authoritative. Unapproved lyrics cannot generate formatted exports. Faster-whisper and Parakeet approved artifacts are both supported.

DEFAULT APPROVED OUTPUT: STANDARD LYRIC SHEET  
USER FORMAT SELECTION: AVAILABLE  
APPROVED LYRIC CONTENT MODIFIED: NO  
A2L APPROVED OUTPUT CAPABILITY: PASS

## Evidence (in repo)

- `a2l/export.py`
- `a2l/app.html` Output screen
- `tests/test_export.py`
- `docs/APPROVED_EXPORT.md`
- `docs/nebula/reports/ACI-A2L-013_COMPLETION_REPORT.md`

## Gaps

- Current approved artifacts do not store song title, artist, or Verse/Chorus labels, so the default sheet is the approved lyric lines with no invented header or section names.
- Previously approved songs get on-demand formatted preview/download; the on-disk `exports/` directory is written at approval time and is not backfilled onto the locked Jay approval without a new approval.
- Copy uses the browser clipboard API; if the browser blocks it, the operator can select the preview text and copy manually.
