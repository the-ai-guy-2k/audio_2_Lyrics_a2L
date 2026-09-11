# ACI-A2L-014 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-014 — Song metadata intake  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. Operators can optionally enter song title and artist at upload, see and correct them during review, and have them preserved on approved JSON for the Standard Lyric Sheet. Missing values are not invented. Lyric words are unchanged.

Not merged. Not pushed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-014-song-metadata` |
| Base | `feature/aci-a2l-013-approved-export-formatting` @ `1518c3c5ae32ba7261db68cf7ba6d40903b8b19d` |
| Implementation | recorded in ACR-A2L-014 after this commit |

## Metadata intake implementation

Upload shows Song title and Artist next to the selected WAV. Both fields are optional. Extract sends them with the file. They are never copied from the filename.

## Persistence behavior

Working copy: `artifacts/ingest/<sha>/song_metadata.json` (`OPERATOR_PROVIDED_SONG_METADATA`, independent of lyric lines and of which engine pipeline is used).

Review JSON also stores `song_title` / `artist`. Save updates both the review and the job-level metadata file.

## Review behavior

Review shows the same two fields. They are editable until APPROVED. Save persists corrections. Save is still not approval.

## Approval behavior

`approved_lyrics.json` retains `song_title` and `artist` when supplied (otherwise JSON `null`). `approved_lyrics.txt` remains the lyric body only. After approval, metadata cannot be changed until explicit reopen; a new revision is required for corrected metadata to become authoritative.

## Output integration

STANDARD LYRIC SHEET prepends available title and/or artist. PLAIN TEXT and STRUCTURED LYRICS keep their existing purposes (canonical lyric body / existing section labels).

## Validation

| Check | Result |
| --- | --- |
| 1. User can enter song title | PASS |
| 2. User can enter artist | PASS |
| 3. Both fields optional | PASS |
| 4. WAV filename is not authoritative metadata | PASS |
| 5. Metadata persists through processing | PASS |
| 6. Metadata appears during review | PASS |
| 7. Metadata can be corrected before approval | PASS |
| 8. Approval preserves metadata in approved JSON | PASS |
| 9. Standard Lyric Sheet displays available metadata | PASS |
| 10. Missing metadata is never invented | PASS |
| 11. Metadata does not modify approved lyric words | PASS |
| 12. Reopen/reapproval preserves authority behavior | PASS |
| 13. Both transcription engines remain functional | PASS |
| 14. Applicable regression tests PASS | PASS — 97 tests |

## Applicable tests

`python -m pytest tests --ignore=tests/test_parakeet_candidate.py`

Result: **97 passed** (Python 3.14.3).

## Errors / warnings

None that blocked the ACI.

The engineering review page (`python -m a2l review`) does not include title/artist intake fields. Operator-app intake is the governed path.

## Out of scope honored

No album, songwriter, publisher, copyright, ISRC, lookup, cover art, new engines, or merge/push.

## Merge / push status

Not merged. Not pushed.
