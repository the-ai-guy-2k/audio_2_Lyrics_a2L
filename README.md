# Audio to Lyrics (A2L)

A2L recovers lyrics from artist-owned/mastered audio.

**Current capability:**

- ACI-ATL-001: WAV ingestion, CONTROL-A working artifact, ingest manifest
- ACI-ATL-002: CONTROL-A machine transcription (non-authoritative draft)
- ACI-ATL-003: uncertainty handling (flag, do not invent)

**Not implemented:** lyric structuring, human approval, approved lyric artifacts, vocal isolation, stem separation, normalization, resampling.

## Governing product rule

Artist-owned/mastered audio is authoritative.

A2L never modifies or replaces the authoritative source artifact. Machine-derived files are working artifacts only.

## Current Truth

Remote: https://github.com/the-ai-guy-2k/audio_2_Lyrics_a2L.git

ACI-ATL-001 started from an empty repository. This branch establishes the first bounded capability: audio ingestion.

## Ingest a WAV

```bash
python -m a2l ingest path/to/mastered.wav --artifact-root artifacts
```

Requires Python 3.11+. Ingest has no third-party runtime dependencies. Transcription uses the OpenAI client when `OPENAI_API_KEY` is set (`pip install -e ".[dev,transcribe]"`).

```bash
pip install -e ".[dev,transcribe]"
python -m pytest
python scripts/validate_aci_atl_001.py
python scripts/validate_aci_atl_002.py
python scripts/validate_aci_atl_003.py
```

## Transcribe CONTROL-A audio

```bash
python -m a2l transcribe artifacts/ingest/<job_id>/ingest_manifest.json
```

Output is a **machine draft**, never approved lyrics. Details: [docs/TRANSCRIPTION.md](docs/TRANSCRIPTION.md)

## Flag uncertainty

```bash
python -m a2l uncertainty artifacts/ingest/<job_id>/machine_transcription/transcription_draft.json
```

This flags questionable spans. It does not rewrite or approve lyrics. Details: [docs/UNCERTAINTY.md](docs/UNCERTAINTY.md)

## Artifact flow

```text
Operator WAV (read-only)
        │
        ▼
   validate WAV
   extract metadata
        │
        ▼
artifacts/ingest/<sha256>/
  authoritative_source/source.wav          AUTHORITATIVE SOURCE (immutable)
  derived_working/transcription_ready.wav  DERIVED WORKING (CONTROL A, untreated)
  ingest_manifest.json                      contract for ACI-ATL-002
  machine_transcription/                   ACI-ATL-002 machine draft (NOT approved lyrics)
    transcription_draft.json
    transcription_draft.txt
  uncertainty/                             ACI-ATL-003 flags (NOT approved lyrics)
    uncertainty_report.json
    uncertainty_report.txt
```

The working artifact is a **byte-identical copy** of the source WAV. No loudness processing, resampling, mono mixdown, or vocal isolation is applied. That preserves untreated mastered audio as CONTROL A for later transcription experiments.

Details: [docs/AUDIO_INGESTION.md](docs/AUDIO_INGESTION.md)

ACI-ATL-002 handoff: [docs/ACI_ATL_002_HANDOFF.md](docs/ACI_ATL_002_HANDOFF.md)

Transcription draft contract: [docs/TRANSCRIPTION_DRAFT_CONTRACT.md](docs/TRANSCRIPTION_DRAFT_CONTRACT.md)

## Branching

Feature work lives on `feature/aci-atl-###` until validated. Do not treat this branch as deployable until an Operator/QEN merge is authorized.
