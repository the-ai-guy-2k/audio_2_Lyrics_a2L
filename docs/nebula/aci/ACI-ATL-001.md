# ACI-ATL-001

AUDIO TO LYRICS (A2L)  
AUDIO INGESTION + BASELINE ARTIFACT PREPARATION

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — AWAITING OPERATOR ACCEPTANCE

Permanent copy of the Operator ACI used for this capability. The executable product behavior is documented in `docs/AUDIO_INGESTION.md` and `docs/ACI_ATL_002_HANDOFF.md`.

## Intent

Establish the first bounded A2L capability: accept a mastered WAV as the authoritative source, validate it, preserve it unchanged, and produce a deterministic transcription-ready working artifact for downstream A2L processing.

## Governing product rule

Artist-owned/mastered audio is authoritative. A2L processing must never modify or replace the authoritative source artifact. Machine-derived artifacts are downstream working artifacts only.

## Explicitly out of scope

Speech/music transcription, lyric generation/formatting, uncertainty detection, lyric correction, LLM interpretation, vocal isolation, Demucs, stem separation, synchronization, production deployment, unrelated UI polish, unrelated refactoring.

## Experimental control

The mastered recording remains usable as untreated CONTROL A. Vocal isolation is not mandatory and is not implemented.
