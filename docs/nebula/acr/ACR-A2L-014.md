# ACR-A2L-014 — ACI-A2L-014 acceptance

**ACI:** ACI-A2L-014 — Song metadata intake  
**Date recorded:** 2026-09-11  
**Branch:** `feature/aci-a2l-014-song-metadata`  
**Commit:** `44a880d`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** optional song title and artist intake; persistence through review/approval; Standard Lyric Sheet uses supplied values only.

## Accepted outcome

The operator can enter Song title and Artist at upload. Both are optional. The WAV filename is not used as the title. Values persist through processing, appear on review, can be corrected before approval, and are stored on `approved_lyrics.json` without changing lyric words. The Standard Lyric Sheet shows available metadata and invents nothing when fields are empty. Faster-whisper and Parakeet paths both work.

SONG TITLE INTAKE: AVAILABLE  
ARTIST INTAKE: AVAILABLE  
METADATA INCLUDED IN APPROVED OUTPUT: YES  
MISSING METADATA INVENTED: NO  
ACI-A2L-014: PASS

## Evidence (in repo)

- `a2l/metadata.py`
- `a2l/app.html` Upload and Review fields
- `tests/test_metadata.py`
- `docs/SONG_METADATA.md`
- `docs/nebula/reports/ACI-A2L-014_COMPLETION_REPORT.md`

## Gaps

- The engineering review page (`python -m a2l review`) does not include title/artist fields. Operator-app intake is the governed path.
- Previously approved songs (including locked Jay revision 2) have no title/artist until the operator enters them and reapproves.
- Album, songwriter, publisher, and lookup fields remain out of scope.
