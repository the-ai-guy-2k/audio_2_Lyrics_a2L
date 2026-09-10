# ACR-A2L-007 — ACI-A2L-007 acceptance

**ACI:** ACI-A2L-007 — Promote faster-whisper large-v3 to primary transcription engine  
**Date recorded:** 2026-09-10  
**Branch:** `feature/aci-a2l-007-primary-faster-whisper`  
**Commit:** `b17b281`  
**Status:** COMPLETE on feature branch — not merged; lyrics not approved  
**Product changes:** `python -m a2l transcribe` now uses faster-whisper / Whisper large-v3; whisper-1 is not the primary path; historical whisper-1 artifacts were not overwritten

## Accepted outcome

`python -m a2l transcribe` invoked faster-whisper 1.2.1 / CTranslate2 4.8.2 / Whisper large-v3 (`Systran/faster-whisper-large-v3`) on the locked mastered WAV. The draft was consumed by uncertainty and structuring without candidate-specific copying. The paragraph-style review UI loaded the primary structured draft. Human corrections persisted. Original master SHA-256 remained `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. whisper-1 `transcription_draft.json` SHA-256 remained `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`. `usable_as_approved_lyrics` remains false.

PRIMARY A2L TRANSCRIPTION ENGINE: faster-whisper / Whisper large-v3  
`python -m a2l transcribe` NOW USES THE PRIMARY ENGINE: YES

## Evidence (in repo)

- `docs/nebula/artifacts/aci-a2l-007-evidence/`
- `tests/test_primary_engine.py`
- `docs/TRANSCRIPTION.md`
- `docs/nebula/reports/ACI-A2L-007_COMPLETION_REPORT.md`

## Gaps

- Primary runtime artifacts live under `a2l_pipeline/` so the frozen whisper-1 folder is not reused.
- Isolated `.venv-faster-whisper` (Python 3.12) is still required on this workstation.
