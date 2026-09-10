# Audio to Lyrics (A2L)

A2L recovers lyrics from artist-owned/mastered audio.

**Current capability:**

- ACI-ATL-001: WAV ingestion, CONTROL-A working artifact, ingest manifest
- ACI-ATL-002: CONTROL-A machine transcription (non-authoritative draft)
- ACI-A2L-007: faster-whisper / Whisper large-v3 is the primary transcription engine
- ACI-ATL-003: uncertainty handling (flag, do not invent)
- ACI-ATL-004: lyric structuring (structure, do not rewrite)
- ACI-A2L-006: human review and correction (reviewed draft, not approved until explicit confirmation)
- ACI-A2L-008: explicit human approval and approved lyric artifacts

**Not implemented:** vocal isolation, stem separation, normalization, resampling, finished application frontend.

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

Requires Python 3.11+. Ingest has no third-party runtime dependencies. Primary transcription uses faster-whisper / Whisper large-v3 (`pip install -e ".[dev,transcribe]"`). On this workstation use isolated `.venv-faster-whisper` (Python 3.12).

```bash
pip install -e ".[dev,transcribe]"
python -m pytest
python scripts/validate_aci_atl_001.py
python scripts/validate_aci_atl_002.py
python scripts/validate_aci_atl_003.py
python scripts/validate_aci_atl_004.py
```

## Transcribe CONTROL-A audio

```bash
python -m a2l transcribe artifacts/ingest/<job_id>/ingest_manifest.json
```

Primary engine is **faster-whisper / Whisper large-v3**. Output is a **machine draft**, never approved lyrics. Historical OpenAI whisper-1 artifacts are not overwritten. Details: [docs/TRANSCRIPTION.md](docs/TRANSCRIPTION.md)

## Flag uncertainty

```bash
python -m a2l uncertainty artifacts/ingest/<job_id>/a2l_pipeline/machine_transcription/transcription_draft.json
```

This flags questionable spans. It does not rewrite or approve lyrics. Details: [docs/UNCERTAINTY.md](docs/UNCERTAINTY.md)

## Structure a lyric draft

```bash
python -m a2l structure artifacts/ingest/<job_id>/a2l_pipeline/uncertainty/uncertainty_report.json
```

This produces a timed, annotated lyric draft for human review. It does not rewrite or approve lyrics. Details: [docs/LYRIC_STRUCTURING.md](docs/LYRIC_STRUCTURING.md)

## Human review and correction

The review UI consumes the primary faster-whisper large-v3 structured draft. Save does not approve lyrics. Approval is a separate explicit operator action.

```bash
python -m a2l review
```

Open http://127.0.0.1:8765/

Details: [docs/HUMAN_REVIEW.md](docs/HUMAN_REVIEW.md)

## Explicit approval

After review, the operator must explicitly mark lyrics APPROVED. That writes:

```text
artifacts/ingest/<sha256>/a2l_pipeline/approved_lyrics/
  approved_lyrics.txt
  approved_lyrics.json
```

The locked Jay song is **APPROVED** (ACI-A2L-009 Amendment 01, revision 2). Prior approval is archived. Details: [docs/APPROVED_LYRICS.md](docs/APPROVED_LYRICS.md)

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
  ingest_manifest.json                      contract for transcription
  machine_transcription/                   HISTORICAL whisper-1 baseline (not overwritten)
    transcription_draft.json
    transcription_draft.txt
  a2l_pipeline/                             PRIMARY faster-whisper / large-v3 path
    machine_transcription/                   ACI-A2L-007 machine draft (NOT approved lyrics)
      transcription_draft.json
      transcription_draft.txt
    uncertainty/                             ACI-ATL-003 flags (NOT approved lyrics)
      uncertainty_report.json
      uncertainty_report.txt
    structured_lyrics/                      ACI-ATL-004 structured draft (NOT approved lyrics)
      structured_lyric_draft.json
      structured_lyric_draft.txt
    human_review/reviewed_lyric_draft.json   ACI-A2L-006 reviewed draft (NOT approved until ACI-A2L-008)
    approved_lyrics/                         ACI-A2L-008 authoritative lyrics (only after explicit approval)
      approved_lyrics.txt
      approved_lyrics.json
```

The working artifact is a **byte-identical copy** of the source WAV. No loudness processing, resampling, mono mixdown, or vocal isolation is applied. That preserves untreated mastered audio as CONTROL A for later transcription experiments.

Details: [docs/AUDIO_INGESTION.md](docs/AUDIO_INGESTION.md)

ACI-ATL-002 handoff: [docs/ACI_ATL_002_HANDOFF.md](docs/ACI_ATL_002_HANDOFF.md)

Transcription draft contract: [docs/TRANSCRIPTION_DRAFT_CONTRACT.md](docs/TRANSCRIPTION_DRAFT_CONTRACT.md)

## Branching

Feature work lives on `feature/aci-atl-###` until validated. Do not treat this branch as deployable until an Operator/QEN merge is authorized.
