# Audio to Lyrics (A2L)

A2L recovers lyrics from artist-owned/mastered audio.

**Current capability (ACI-ATL-001):** WAV ingestion, validation, metadata extraction, and CONTROL-A working-artifact preparation.

**Not implemented:** transcription, lyric generation, vocal isolation, stem separation, normalization, resampling.

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

Requires Python 3.11+. Runtime dependencies: none (standard library only).

```bash
pip install -e ".[dev]"
python -m pytest
python scripts/validate_aci_atl_001.py
```

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
```

The working artifact is a **byte-identical copy** of the source WAV. No loudness processing, resampling, mono mixdown, or vocal isolation is applied. That preserves untreated mastered audio as CONTROL A for later transcription experiments.

Details: [docs/AUDIO_INGESTION.md](docs/AUDIO_INGESTION.md)

ACI-ATL-002 handoff: [docs/ACI_ATL_002_HANDOFF.md](docs/ACI_ATL_002_HANDOFF.md)

## Branching

Feature work lives on `feature/aci-atl-001` until validated. Do not treat this branch as deployable until an Operator/QEN merge is authorized.
