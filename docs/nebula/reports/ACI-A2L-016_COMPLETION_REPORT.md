# ACI-A2L-016 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-016 — Metadata-based export filenames  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. User-downloaded lyric files are named from operator-supplied Artist and Song Title. Approved lyric words are unchanged. Canonical `approved_lyrics.txt` / `approved_lyrics.json` names and stored metadata are unchanged.

Not merged. Not pushed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-016-export-filenames` |
| Base | `feature/aci-a2l-015-release-readiness` @ `f9532c95dfd77c6cb7f4023a3d1d7623999a5dc5` |
| Implementation | `af300ab` |

## Filename-generation implementation

`a2l/export.py` `export_download_name()` builds the user-facing `download_name` from approved JSON `song_title`/`title` and `artist`. `GET /export/output.txt` sets `Content-Disposition` from that name. The Output download link also sets the HTML `download` attribute. WAV filenames are not consulted.

## Sanitization behavior

Invalid filesystem characters (`<>:"/\\|?*` and controls), directory separators, and Windows reserved device names are removed or treated as missing. Leading/trailing dots and spaces are stripped. Empty results after sanitization fall back to `lyrics.txt`. Path traversal sequences cannot produce a path; the result is always a basename ending in `.txt`. Stored title/artist on `approved_lyrics.json` are not rewritten.

## Fallback behavior

| Metadata | STANDARD LYRIC SHEET filename |
| --- | --- |
| Artist + Song Title | `<Artist> - <Song Title>.txt` |
| Song Title only | `<Song Title>.txt` |
| Artist only | `<Artist> - Lyrics.txt` |
| Neither | `lyrics.txt` |

## Output-format naming behavior

PLAIN TEXT appends ` - Plain Text` before `.txt`. STRUCTURED LYRICS appends ` - Structured Lyrics` before `.txt`. The same partial-metadata fallbacks apply (`lyrics - Plain Text.txt` when neither field exists).

Internal derived files under `approved_lyrics/exports/` remain `lyric-sheet.txt`, `lyrics.txt`, and `structured-lyrics.txt`.

## Validation

| Check | Result |
| --- | --- |
| 1. Artist + title → `<Artist> - <Song Title>.txt` | PASS |
| 2. Title only → `<Song Title>.txt` | PASS |
| 3. Artist only → `<Artist> - Lyrics.txt` | PASS |
| 4. Missing metadata → `lyrics.txt` | PASS |
| 5. Plain Text suffix | PASS |
| 6. Structured Lyrics suffix | PASS |
| 7. Invalid filename characters handled | PASS |
| 8. Path traversal impossible | PASS |
| 9. Approved lyric content unchanged | PASS |
| 10. `approved_lyrics.json` metadata unchanged | PASS |
| 11. Copy/preview/download remain functional | PASS |
| 12. Applicable regression tests PASS | PASS — 104 tests |

## Applicable tests

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py`

Result: **104 passed** (Python 3.14.3).

## Errors / warnings

None that blocked the ACI.

The 015 working tree contained an operator Extract-button JavaScript parse fix (`displayText` restored). That repair is included on this branch so the application remains usable. It does not change lyric content or filename rules.

Default Python 3.14 still cannot extract with faster-whisper; the supported extract start remains `.venv-faster-whisper`.

## Out of scope honored

No lyric formatting change, no intake-field change, no new metadata fields, no new export formats, no frontend redesign, canonical authority files not renamed, not merged, not pushed.

## Merge / push status

Not merged. Not pushed.

## Commit information

Implementation SHA is `af300ab` on `feature/aci-a2l-016-export-filenames`.
