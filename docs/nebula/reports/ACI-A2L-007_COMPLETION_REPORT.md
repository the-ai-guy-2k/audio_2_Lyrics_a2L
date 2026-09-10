# ACI-A2L-007 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-007 — Promote faster-whisper large-v3 to primary transcription engine  
**Amendment:** 01 — primary transcription pipeline completion report  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged; not approved lyrics)

---

## Execution status

COMPLETE on bounded feature branch. Amendment 01 did not rerun locked-song transcription. It verified existing ACI-A2L-007 execution evidence plus cheap SHA, HTTP, artifact-path, and regression checks.

The previous review server on port 8765 was **intentionally stopped** so the primary-path review interface could take over. That is expected execution behavior and is **not** a review failure.

Not merged. Not pushed. Approval/export not started.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-007-primary-faster-whisper` |
| Base | `feature/aci-a2l-006-human-review` @ `a63732345290fdbb7bf33924816aaeea1aa20473` |
| Implementation | `b17b28109de29439a4154aed0830bc657ee25fc5` |
| ACR / traceability record | `0e1acec137b6523745f9f57f544e3c2d3b7fc218` |

Did not branch from parked Parakeet work.

## Engine

| Field | Value |
| --- | --- |
| faster-whisper | 1.2.1 |
| CTranslate2 | 4.8.2 |
| Model identifier | Whisper `large-v3` (`Systran/faster-whisper-large-v3`) |
| Device / compute | CPU / `int8` |
| Runtime used for locked-song transcribe | `.venv-faster-whisper` (Python 3.12.10) |

## Primary transcription command behavior

`python -m a2l transcribe` calls `transcribe_from_manifest()`, which defaults to `FasterWhisperEngine()` (`a2l/transcribe.py`). OpenAI whisper-1 is not the primary runtime path.

Locked-song command used:

```text
.venv-faster-whisper\Scripts\python.exe -m a2l transcribe artifacts/ingest/bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be/ingest_manifest.json
```

Result: `ok: true`, `engine.technology=faster-whisper`, `engine.model=large-v3`, `usable_as_approved_lyrics=false`.

## Downstream artifact flow

```text
WAV
  → ingest
  → python -m a2l transcribe          (faster-whisper / large-v3)
  → python -m a2l uncertainty        (primary transcription draft)
  → python -m a2l structure
  → python -m a2l review
```

Primary artifacts (no candidate-folder copy required):

```text
artifacts/ingest/<sha>/a2l_pipeline/
  machine_transcription/transcription_draft.json
  uncertainty/uncertainty_report.json
  structured_lyrics/structured_lyric_draft.json
  human_review/reviewed_lyric_draft.json
```

Historical whisper-1 remains at `artifacts/ingest/<sha>/machine_transcription/` and was not overwritten.

## Primary review artifact location

`C:\Users\tim\Documents\business_related\The_AI_Guy\nebula\2 - TAIG2K_SOFTWARE\audio_2_lyrics_a2l\artifacts\ingest\bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be\a2l_pipeline\human_review\reviewed_lyric_draft.json`

Repo copy: `docs/nebula/artifacts/aci-a2l-007-evidence/reviewed_lyric_draft.json`

## Human-review interface location

**http://127.0.0.1:8765/**

Command: `python -m a2l review`

Amendment 01 confirmed HTTP 200. The running server serves the primary pipeline draft under `a2l_pipeline/human_review/`.

## Required-evidence checklist

| # | Requirement | Result |
| --- | --- | --- |
| 1 | `python -m a2l transcribe` uses faster-whisper / large-v3 as primary | **YES** |
| 2 | Normal primary pipeline is ingest → faster-whisper → uncertainty → structure → review | **YES** |
| 3 | Downstream consumes primary artifacts without candidate-specific manual copying | **YES** |
| 4 | Primary-path review loads the structured lyric draft | **YES** |
| 5 | Paragraph-style lyric presentation remains functional | **YES** (`#lyrics` inline wrapping phrases; amber uncertainty; underlined corrections) |
| 6 | Human correction / save / reload remain functional | **YES** |
| 7 | Machine text remains traceable separately from human text | **YES** |
| 8 | Locked source WAV unchanged | **YES** |
| 9 | Applicable regression tests PASS | **YES** (55 passed) |

Locked-song human-review persistence (not a full lyric pass):

| Line | Machine (unchanged) | Human | Source |
| --- | --- | --- | --- |
| L27 | `Hey, something we can stall to` | `Hey, something we can stomp to` | `HUMAN_CORRECTED` |
| L36 | `Hunkers with that old school funk` | `Hook us with that old school funk` | `HUMAN_CORRECTED` |
| L40 | `Play something we can start to` | `Play something we can stomp to` | `HUMAN_CORRECTED` |

Authority remains `NON_AUTHORITATIVE_REVIEWED_DRAFT`. Lyrics are not approved.

## Locked-song validation result

Ingest succeeded (`byte_identical: true`). Primary transcribe, uncertainty, and structure wrote under `a2l_pipeline/`. Review loaded that structured draft as wrapping paragraph text. Save/reload kept corrections. Machine text was not overwritten.

Amendment 01 reconfirmed: source SHA, whisper-1 SHA, all four primary pipeline files present, review HTTP 200.

## Regression test results

`py -3.14 -m pytest tests/test_ingest.py tests/test_transcribe.py tests/test_uncertainty.py tests/test_structure.py tests/test_faster_whisper_candidate.py tests/test_review.py tests/test_primary_engine.py --ignore=tests/test_parakeet_candidate.py`

**55 passed.** Untracked Parakeet test was not collected. Expensive locked-song transcription was not rerun for this amendment.

## Source SHA verification

- Locked master: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- whisper-1 `transcription_draft.json`: `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471` (unchanged)

## Errors / warnings

No blocking errors. The stopped 8765 process from the prior candidate-path server is expected and is not a review failure.

faster-whisper reported no engine warnings on the locked-song transcribe. Machine flags `NO_SPEECH_LIKELY` / `POSSIBLE_HALLUCINATION` were preserved and passed to uncertainty (flag, do not invent).

## Merge status

**NOT MERGED.**

## Push status

**NOT PUSHED.**

## Remaining risks

- Primary runtime uses `a2l_pipeline/` beside frozen whisper-1; operators must use the documented pipeline paths.
- Locked-song transcribe still depends on `.venv-faster-whisper` (Python 3.12) on this workstation.
- Remaining machine errors (including `Thanks for watching!`) were not cleaned. This ACI did not run a full lyric pass.
- Lyrics remain non-authoritative. Approval/export was not started.

## Recommendation

**PASS** for promoting the validated transcription engine into the primary A2L path.

Not a lyric-quality PASS. Not an approval PASS.

---

PRIMARY A2L TRANSCRIPTION ENGINE:  
faster-whisper / Whisper large-v3

`python -m a2l transcribe`  
USES PRIMARY ENGINE: **YES**

PRIMARY PIPELINE HUMAN REVIEW ARTIFACT:  
`C:\Users\tim\Documents\business_related\The_AI_Guy\nebula\2 - TAIG2K_SOFTWARE\audio_2_lyrics_a2l\artifacts\ingest\bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be\a2l_pipeline\human_review\reviewed_lyric_draft.json`

---

## Minority Report

1. Primary drafts are stored under `a2l_pipeline/` rather than replacing the historical `machine_transcription/` folder. That preserves whisper-1 evidence.

2. This workstation still runs the model from `.venv-faster-whisper` (Python 3.12.10). Python 3.14 used for tests does not have faster-whisper installed.

3. OpenAI `whisper-1` code remains for historical tests. It is not invoked by `python -m a2l transcribe`.

4. `Thanks for watching!` and other remaining machine errors are still in the draft.

5. Candidate `artifacts/candidates/faster-whisper-large-v3/` still exists. It is not required for the normal pipeline. Review can merge prior corrections from it when the primary review file is first created.
