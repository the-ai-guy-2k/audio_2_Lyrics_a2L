# ACR-A2L-REL-001 — ACI-A2L-REL-001 acceptance

**ACI:** ACI-A2L-REL-001 — Song release record  
**Date recorded:** 2026-09-11  
**Branch:** `feature/aci-a2l-rel-001-song-release-record`  
**Commit:** `d5c0d7a`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** per-song release Current Truth record in the existing operator application; missing fields flagged; not distribution.

## Accepted outcome

An ingested song can carry a persistent Song Release Record. Existing title, artist, duration, master audio, and approved-lyric availability are reused. Operator-entered credits/rights/ISRC persist. Missing stays MISSING. READY/INCOMPLETE is internal completeness. Approved lyric words and authority are unchanged. ISRC is never generated.

SONG RELEASE RECORD: AVAILABLE  
OPERATOR UI: AVAILABLE  
PERSISTENCE: PASS  
RELEASE READINESS: AVAILABLE  
APPROVED LYRIC AUTHORITY MODIFIED: NO  
RELEASE DATA INVENTED: NO  
ACI-A2L-REL-001: PASS

## Evidence (in repo)

- `a2l/release_record.py`
- `a2l/app.html` Release screen
- `tests/test_release_record.py`
- `docs/SONG_RELEASE_RECORD.md`
- `docs/nebula/reports/ACI-A2L-REL-001_COMPLETION_REPORT.md`

## Gaps

- Album-level sequencing, UPC, distributor delivery, and registrations remain out of scope.
- Engineering review page (`python -m a2l review`) does not include the release record. Operator-app Release is the governed path.
- Previously ingested songs have no record until the operator opens/saves Release.
