# ACI-A2L-007 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-007 — Promote faster-whisper large-v3 to primary transcription engine  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged; not approved lyrics)

---

## Execution status

COMPLETE on bounded feature branch. Not merged. Not pushed. Approval/export not started.

## Branch

`feature/aci-a2l-007-primary-faster-whisper`  
**Base:** `feature/aci-a2l-006-human-review` @ `a63732345290fdbb7bf33924816aaeea1aa20473`

## Implementation summary

`python -m a2l transcribe` now defaults to `FasterWhisperEngine` (faster-whisper / Whisper large-v3) using the validated ACI-A2L-005 configuration (CPU / int8). OpenAI whisper-1 is no longer the primary runtime path. Historical whisper-1 files remain at `artifacts/ingest/<sha>/machine_transcription/`.

Primary downstream artifacts are written under `artifacts/ingest/<sha>/a2l_pipeline/` so uncertainty, structuring, and human review consume the new draft without copying candidate files by hand.

## Engine

| Field | Value |
| --- | --- |
| Engine | faster-whisper 1.2.1 |
| CTranslate2 | 4.8.2 |
| Model | `large-v3` / `Systran/faster-whisper-large-v3` |
| Device | CPU / int8 |

## Artifact flow

```text
WAV → ingest → python -m a2l transcribe (faster-whisper large-v3)
    → python -m a2l uncertainty <a2l_pipeline/.../transcription_draft.json>
    → python -m a2l structure <a2l_pipeline/uncertainty/uncertainty_report.json>
    → python -m a2l review
```

## Tests performed

`py -3.14 -m pytest` ingest, transcribe, uncertainty, structure, faster-whisper candidate isolation, review, and primary-engine tests — **PASS** (55 tests). Untracked Parakeet test was not collected.

Locked-song runtime: ingest; `python -m a2l transcribe` (`.venv-faster-whisper`); uncertainty; structure; paragraph review UI; save/reload. L27/L36 prior corrections merged; L40 `start` → `stomp` persisted.

## Fixed-song validation

Source SHA-256 unchanged: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.  
whisper-1 `transcription_draft.json` SHA-256 unchanged: `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`.

## Errors / warnings

faster-whisper reported no engine warnings on the locked-song run. `NO_SPEECH_LIKELY` / `POSSIBLE_HALLUCINATION` flags were raised on machine output and passed to uncertainty (flag, do not invent).

## Commit information

Implementation commit is on `feature/aci-a2l-007-primary-faster-whisper`.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Recommendation

**PASS** for promoting the validated transcription engine. Not a lyric-quality or approval PASS.

---

## Minority Report

1. Primary drafts are stored under `a2l_pipeline/` rather than replacing the historical `machine_transcription/` folder. That preserves whisper-1 evidence. Operators must point uncertainty/structure at the pipeline paths (documented).

2. This workstation still runs the model from `.venv-faster-whisper` (Python 3.12.10). Python 3.14 used for tests does not have faster-whisper installed.

3. OpenAI `whisper-1` code remains for historical tests. It is not invoked by `python -m a2l transcribe`.

4. `Thanks for watching!` and remaining machine errors are still in the draft. This ACI did not run a full lyric pass.

5. Candidate `artifacts/candidates/faster-whisper-large-v3/` still exists. Review can merge prior corrections from it. It is not required for the normal pipeline.
