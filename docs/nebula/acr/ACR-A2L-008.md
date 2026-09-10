# ACR-A2L-008 — ACI-A2L-008 acceptance

**ACI:** ACI-A2L-008 — Approved lyric artifact  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-008-approved-lyrics`  
**Commit:** `ae12419`  
**Status:** COMPLETE on feature branch — not merged; locked song not approved  
**Product changes:** explicit `confirm=true` approval; `approved_lyrics.txt` / `approved_lyrics.json`; DRAFT / REVIEWED / APPROVED display

## Accepted outcome

The review UI can save corrections without approving. Explicit operator confirmation writes clean approved lyrics plus a provenance JSON. Fixture tests proved that path. The locked Jay song remains `NOT_APPROVED` with no approved files on disk. Original master SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. whisper-1 `transcription_draft.json` SHA-256 remained `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`.

REAL LOCKED SONG APPROVAL STATE: NOT APPROVED  
APPROVED LYRIC TXT LOCATION: NOT CREATED  
APPROVED LYRIC JSON LOCATION: NOT CREATED

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-008-evidence/`
- `tests/test_approve.py`
- `docs/APPROVED_LYRICS.md`
- `docs/APPROVED_LYRICS_CONTRACT.md`
- `docs/nebula/reports/ACI-A2L-008_COMPLETION_REPORT.md`

## Gaps

- Approval is on the local stdlib review page, not a product frontend.
- There is no separate `python -m a2l approve` CLI command; approval is `POST /api/approve`.
- The locked song still has remaining machine errors and is intentionally unapproved.
