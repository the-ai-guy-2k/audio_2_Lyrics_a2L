# ACR-ATL-003 — ACI-ATL-003 acceptance

**ACI:** ACI-ATL-003 — Uncertainty handling  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-atl-003`  
**Commit:** `73c71aa`  
**Status:** COMPLETE on feature branch — not merged to deployable  
**Product changes:** uncertainty report over ACI-ATL-002 drafts; 24-bit energy; Whisper API chunked upload for files over 25 MB

## Accepted outcome

The fixed test song is `01Stomp to MIX MSTR 24bit_48hz.wav` (SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`). The original master was not modified.

CONTROL-A ingest, CONTROL-A transcription, and uncertainty handling ran on that song. Machine text was preserved. Uncertainty flags were applied. Output is not approved lyrics. No established lyrics were produced. Transcription accuracy is not claimed.

Live uncertainty: 32 spans, 20 `REQUIRES_LATER_RESOLUTION`, 12 `UNVERIFIED_MACHINE_TEXT`, 0 established. Flags included `WHISPER_BOILERPLATE` (`Thanks for watching!`), `REPEATED_SEGMENT`, `CHUNK_BOUNDARY`, `NO_SPEECH_LIKELY`, `POSSIBLE_HALLUCINATION`.

## Evidence (in repo)

- `docs/nebula/FIXED_TEST_SONG.md`
- `docs/nebula/artifacts/aci-atl-003-evidence/`
- `tests/test_uncertainty.py`
- `docs/nebula/reports/ACI-ATL-003_COMPLETION_REPORT.md`

## Gaps

- GVCA-ATL-001 / ACICE-ATL-001 were not in the repository.
- Whisper `no_speech_prob` on a mastered mix is noisy and over-flags some lyric-like spans.
- Chunked API upload was required because the 24-bit master exceeds 25 MB.
