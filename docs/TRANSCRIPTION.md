# CONTROL-A transcription (ACI-ATL-002)

This document describes the bounded transcription capability. Machine output is a draft, never approved lyrics.

## Purpose

Recover a **machine transcription** directly from the untreated mastered mix (CONTROL A) produced by ACI-ATL-001, **before** any vocal isolation.

## Input contract

Primary input is `ingest_manifest.json` from ACI-ATL-001. See [ACI_ATL_002_HANDOFF.md](ACI_ATL_002_HANDOFF.md).

```bash
python -m a2l ingest path/to/mastered.wav --artifact-root artifacts
python -m a2l transcribe artifacts/ingest/<job_id>/ingest_manifest.json
```

The transcriber:

1. Reads the ingest manifest.
2. Uses `derived_working.relative_path` (`transcription_ready.wav`).
3. Verifies SHA-256 of working and source files.
4. Refuses CONTROL B/C, preprocessing, and vocal isolation.
5. Does not modify `authoritative_source/source.wav` or the working WAV.

## Engine (primary, ACI-A2L-007)

| Field | Value |
| --- | --- |
| Technology | faster-whisper |
| Model | Whisper `large-v3` (`Systran/faster-whisper-large-v3`) |
| Device | CPU |
| `compute_type` | `int8` |
| `language` | `en` |
| `temperature` | `0` |
| `vad_filter` | `false` |
| `condition_on_previous_text` | `false` |

`python -m a2l transcribe` uses this engine. OpenAI `whisper-1` is not the primary path. Historical whisper-1 drafts under `artifacts/ingest/<sha>/machine_transcription/` are not overwritten.

Local validated runtime on this workstation: isolated `.venv-faster-whisper` (Python 3.12). Vocal isolation remains unauthorized.

## FLAG IT — DO NOT INVENT IT

- Output authority is always `NON_AUTHORITATIVE_MACHINE_DRAFT`.
- `approval_status` is always `NOT_APPROVED`.
- `usable_as_approved_lyrics` is always `false`.
- Near-silent PCM is flagged `NO_SIGNAL`. If the engine still returns text, it is preserved as `engine_text` and flagged `ENGINE_TEXT_ON_NO_SIGNAL` / `DO_NOT_TREAT_AS_LYRICS`. The text is not rewritten into plausible lyrics.
- Segment `avg_logprob`, `no_speech_prob`, and `compression_ratio` are flagged when they miss Whisper's published reliability thresholds. Low-confidence text is not deleted and not "cleaned" by an LLM.

## Output artifacts

```text
artifacts/ingest/<sha256>/
  machine_transcription/          HISTORICAL whisper-1 baseline (do not overwrite)
  a2l_pipeline/machine_transcription/
    transcription_draft.json
    transcription_draft.txt
```

The next A2L capability must consume the **primary** `a2l_pipeline/machine_transcription/transcription_draft.json` and must not treat it as approved lyrics. Contract: [TRANSCRIPTION_DRAFT_CONTRACT.md](TRANSCRIPTION_DRAFT_CONTRACT.md).

## Not in this ACI

Lyric structuring, human approval, approved lyric artifacts, vocal isolation, Demucs, CONTROL B/C, UI.
