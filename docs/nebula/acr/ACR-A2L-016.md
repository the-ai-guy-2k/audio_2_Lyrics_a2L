# ACR-A2L-016 — ACI-A2L-016 acceptance

**ACI:** ACI-A2L-016 — Metadata-based export filenames  
**Date recorded:** 2026-09-11  
**Branch:** `feature/aci-a2l-016-export-filenames`  
**Commit:** `af300ab`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** user-downloaded lyric filenames from operator-supplied artist and song title; sanitization of download names only.

## Accepted outcome

Downloaded Standard Lyric Sheet, Plain Text, and Structured Lyrics files are named from operator-entered Artist and Song Title. Missing fields are not invented. The WAV filename is not used. Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain named and worded as before. Invalid filename characters and path traversal cannot escape the download basename.

METADATA-BASED DOWNLOAD FILENAMES: AVAILABLE  
APPROVED LYRIC CONTENT MODIFIED: NO  
ACI-A2L-016: PASS

## Evidence (in repo)

- `a2l/export.py` (`export_download_name`, `sanitize_filename_component`)
- `a2l/app_server.py` Content-Disposition
- `tests/test_export.py` filename cases
- `docs/APPROVED_EXPORT.md`
- `docs/nebula/reports/ACI-A2L-016_COMPLETION_REPORT.md`

## Gaps

- Songs approved before title/artist were entered still download as `lyrics.txt` until the operator supplies metadata and reapproves.
- Internal derived files under `approved_lyrics/exports/` keep stable engineering names (`lyric-sheet.txt`, etc.); only the user download name changed.
- The 015 working-tree Extract-button `displayText` repair is on this branch so the UI remains usable.
