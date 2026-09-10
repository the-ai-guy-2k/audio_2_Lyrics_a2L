# ACR-A2L-009 — ACI-A2L-009 acceptance

**ACI:** ACI-A2L-009 — Real-song end-to-end validation  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-009-real-song-validation`  
**Commit:** `41415d5`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** none (validation). Tests/docs updated to record Operator approval of the locked song.

## Accepted outcome

The locked Jay master traversed ingest → faster-whisper / large-v3 → uncertainty → structuring → human review → explicit Operator approval → approved TXT/JSON. Source SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. whisper-1 drafts unchanged. Reload still shows APPROVED.

REAL LOCKED SONG: APPROVED  
END-TO-END A2L VALIDATION: PARTIAL PASS

The approved TXT still contains previously flagged machine leftovers (`Thanks for watching!` and uncorrected `Play something we can start to` repeats). Operator approval is authoritative; CAE did not rewrite those lines.

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-009-evidence/`
- `tests/test_approve.py`
- `docs/nebula/reports/ACI-A2L-009_COMPLETION_REPORT.md`

## Gaps

- Authoritative TXT includes remaining machine leftovers the Operator did not correct before Approve.
- Local stdlib review UI, not a product frontend.
- Transcription time was not remeasured; ACI-A2L-005 recorded 112.79 s processing.
