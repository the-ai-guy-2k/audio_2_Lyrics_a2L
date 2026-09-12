# ACI-A2L-REL-001 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-REL-001 — Song release record  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. Operators can open, fill, save, and reopen a per-song release record in the existing application. Known A2L truth is reused. Missing fields stay MISSING. Approved lyric words are unchanged.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-rel-001-song-release-record` |
| Base | `deployable` @ `18852ffd4db0eae611b0c1cff9609af93090d88d` |
| Implementation | recorded in follow-up ACR commit |

## Filename-generation / persistence

Artifact: `artifacts/ingest/<sha>/song_release_record.json`

## Required vs optional

READY requires: Song Title, Primary Artist, Track Duration, Explicit/Clean, Songwriter(s), Copyright Year, Copyright Owner, Approved Lyrics.

Optional: Featured Artist(s), Track Number, Disc Number, Composer(s), Producer(s), Publisher, ISRC.

## Validation

| Check | Result |
| --- | --- |
| Record created for ingested song | PASS |
| Existing title/artist reused | PASS |
| Duration from audio truth | PASS |
| Master audio represented | PASS |
| Operator enter/save/reload | PASS |
| Missing stays MISSING | PASS |
| No invented values / no generated ISRC | PASS |
| Approved lyrics status + words unchanged | PASS |
| READY/INCOMPLETE deterministic | PASS |
| Optional fields do not block READY | PASS |
| Export filenames and formats remain | PASS |
| Regression | PASS — 112 tests |

## Applicable tests

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py`

Result: **112 passed** (Python 3.14.3).

## Errors / warnings

None that blocked the ACI.

## Merge / push status

Not merged. Not pushed.
