# Audio to Lyrics (A2L)

A2L recovers lyrics from artist-owned/mastered audio.

**Release baseline:** `deployable` (ACI-A2L-017, sourced from validated ACI-A2L-016). New feature work branches from `deployable`.

## Operator application (product-facing)

This is the supported product path.

**PRIMARY engine:** faster-whisper / Whisper large-v3  
**ALTERNATE engine:** NVIDIA Parakeet / TDT-0.6B-V2 (optional; not promoted)

Primary supported local start (this workstation):

```bash
.venv-faster-whisper\Scripts\python.exe -m a2l app
```

Open **http://127.0.0.1:8780/**

Full procedure, venv setup, and Parakeet alternate start: [docs/OPERATOR_START.md](docs/OPERATOR_START.md)

Default `python` on this workstation is Python 3.14. It can open the UI after `pip install -e ".[dev]"`, but it does **not** include faster-whisper. Extract with the primary engine requires the isolated Python 3.12 `.venv-faster-whisper` above. If that dependency is missing, extract reports that the engine is unavailable; it does not silently invent lyrics.

## Engineering review interface (not the product path)

```bash
python -m a2l review
```

Open **http://127.0.0.1:8765/**

This is the engineering review page. It is not the operator application. Operators use http://127.0.0.1:8780/. Details: [docs/HUMAN_REVIEW.md](docs/HUMAN_REVIEW.md)

## Current capability

- ACI-ATL-001: WAV ingestion, CONTROL-A working artifact, ingest manifest
- ACI-ATL-002: CONTROL-A machine transcription (non-authoritative draft)
- ACI-A2L-007: faster-whisper / Whisper large-v3 is the **primary** transcription engine
- ACI-A2L-012: NVIDIA Parakeet / TDT-0.6B-V2 is an **alternate** engine (not promoted)
- ACI-ATL-003: uncertainty handling (flag, do not invent)
- ACI-ATL-004: lyric structuring (structure, do not rewrite)
- ACI-A2L-006: human review and correction (reviewed draft, not approved until explicit confirmation)
- ACI-A2L-008: explicit human approval and approved lyric artifacts
- ACI-A2L-010: operator application frontend
- ACI-A2L-013: derived Standard Lyric Sheet after approval
- ACI-A2L-014: optional song title and artist (WAV filename is not the title)
- ACI-A2L-016: download filenames from operator-supplied title/artist

**Not implemented:** vocal isolation, stem separation, normalization, resampling, cloud deploy.

## Governing product rule

Artist-owned/mastered audio is authoritative.

A2L never modifies or replaces the authoritative source artifact. Machine-derived files are working artifacts only. FLAG IT — DO NOT INVENT IT.

## Current Truth

Remote: https://github.com/the-ai-guy-2k/audio_2_Lyrics_a2L.git

The formal validated release branch is `deployable`.

## Application workflow

Upload WAV → optional Song title / Artist → Extract lyrics → Review / correct → Approve → Output (Standard Lyric Sheet, with optional Plain Text / Structured Lyrics). Download names use supplied metadata when present. **Release** holds the per-song release record. **Album** organizes those records into an Operator-ordered album view.

Details: [docs/FRONTEND.md](docs/FRONTEND.md), [docs/SONG_METADATA.md](docs/SONG_METADATA.md), [docs/APPROVED_EXPORT.md](docs/APPROVED_EXPORT.md), [docs/SONG_RELEASE_RECORD.md](docs/SONG_RELEASE_RECORD.md), [docs/ALBUM_RELEASE_MANIFEST.md](docs/ALBUM_RELEASE_MANIFEST.md)

The locked Jay song is **APPROVED** (ACI-A2L-009 Amendment 01, revision 2). Details: [docs/APPROVED_LYRICS.md](docs/APPROVED_LYRICS.md)

## Engineering CLI (not required to use the operator application)

```bash
python -m a2l ingest path/to/mastered.wav --artifact-root artifacts
python -m a2l transcribe artifacts/ingest/<job_id>/ingest_manifest.json
python -m a2l uncertainty artifacts/ingest/<job_id>/a2l_pipeline/machine_transcription/transcription_draft.json
python -m a2l structure artifacts/ingest/<job_id>/a2l_pipeline/uncertainty/uncertainty_report.json
```

Ingest has no third-party runtime dependencies. Primary transcription uses faster-whisper / Whisper large-v3 in `.venv-faster-whisper` (`pip install -e ".[dev,transcribe]"` on Python 3.12). Tests: `python -m pytest` (ignore untracked parked Parakeet-candidate helpers).

Contracts: [docs/AUDIO_INGESTION.md](docs/AUDIO_INGESTION.md), [docs/TRANSCRIPTION.md](docs/TRANSCRIPTION.md), [docs/UNCERTAINTY.md](docs/UNCERTAINTY.md), [docs/LYRIC_STRUCTURING.md](docs/LYRIC_STRUCTURING.md)

## Artifact flow

```text
Operator WAV (read-only)
        │
        ▼
artifacts/ingest/<sha256>/
  authoritative_source/source.wav          AUTHORITATIVE SOURCE (immutable)
  derived_working/transcription_ready.wav  DERIVED WORKING (CONTROL A, untreated)
  ingest_manifest.json
  machine_transcription/                   HISTORICAL whisper-1 baseline (not overwritten)
  a2l_pipeline/                            PRIMARY faster-whisper / large-v3 path
    ... uncertainty / structured_lyrics / human_review ...
    approved_lyrics/                       authoritative lyrics (only after explicit approval)
      approved_lyrics.txt
      approved_lyrics.json
      exports/                             derived presentations (not a substitute)
  a2l_pipeline_parakeet/                   ALTERNATE Parakeet path (not promoted)
```

The working WAV is a **byte-identical copy** of the source. No loudness processing, resampling, mono mixdown, or vocal isolation is applied.

## Branching

New A2L capabilities branch from `deployable`. Feature ACI branches are not the release baseline until promoted.
