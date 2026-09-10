# ACR-A2L-009 — ACI-A2L-009 acceptance

**ACI:** ACI-A2L-009 — Real-song end-to-end validation  
**Amendment:** 01  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-009-real-song-validation`  
**Commit:** `b64b85f`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** explicit reopen/reapproval; review vs approved authority split. Validation only for the locked song.

## Accepted outcome

The locked Jay master traversed ingest → faster-whisper / large-v3 → uncertainty → structuring → human review → explicit Operator approval → explicit reopen → Operator reapproval. Source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. whisper-1 drafts unchanged. Current state is APPROVED (revision 2). Revision 1 remains in `approved_lyrics/history/`. Review record authority is `HUMAN_REVIEW_PROVENANCE`; active lyric authority is `AUTHORITATIVE_APPROVED_LYRICS`.

REAL LOCKED SONG: APPROVED (revision 2)  
END-TO-END A2L VALIDATION: PARTIAL PASS

The revision-2 TXT lyric body is SHA-identical to revision 1 and still contains previously flagged leftovers (`Thanks for watching!`, uncorrected `start to` repeats, `bored loose`). Operator approval is authoritative; CAE did not rewrite those lines.

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-009-evidence/`
- `tests/test_approve.py`
- `docs/nebula/reports/ACI-A2L-009_COMPLETION_REPORT.md`

## Gaps

- Authoritative TXT includes remaining machine leftovers after reopen/reapproval.
- Local stdlib review UI, not a product frontend.
- Transcription time was not remeasured; ACI-A2L-005 recorded 112.79 s processing.
