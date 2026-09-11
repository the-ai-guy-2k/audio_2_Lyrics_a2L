# ACI-A2L-010 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-010 — A2L application frontend  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. The existing pipeline is unchanged. The frontend coordinates ingest, transcription, uncertainty, structuring, review, approval, and export as one operator workflow.

Not merged. Not pushed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-010-frontend` |
| Base | `feature/aci-a2l-009-real-song-validation` @ `209569359f500cb8986743a5cb603ca59b95807d` |

## Frontend architecture

Stdlib `ThreadingHTTPServer` in `a2l/app_server.py` serves `a2l/app.html`.

```text
Browser
  → POST /api/extract (WAV upload, temp copy, ingest_wav)
  → ingest → faster-whisper / large-v3 → uncertainty → structure → review draft
  → GET /api/state + POST /api/save (review, not approval)
  → POST /api/approve {confirm: true}
  → GET /export/approved_lyrics.txt (+ optional JSON)
  → POST /api/reopen {confirm: true} when an approved artifact is edited again
```

The original operator file is never a write target. Processing status is operator language only.

## Start

```bash
python -m a2l app
```

URL: http://127.0.0.1:8780/

## Workflow validation

| Check | Result |
| --- | --- |
| Application loads | YES |
| Valid WAV upload | YES (fixture) |
| Invalid input rejected | YES |
| Established pipeline started | YES |
| Primary engine faster-whisper / large-v3 | YES (app default; tests use ScriptedEngine with those labels) |
| Processing status shown | YES |
| Paragraph-style review | YES |
| Human correction | YES |
| Save without approval | YES |
| Explicit approval required | YES (`confirm: true`) |
| APPROVED state displayed | YES |
| approved_lyrics.txt after approval | YES |
| Provenance preserved | YES (JSON approval_event.automatic false; machine_text retained) |
| Source recording integrity | YES (fixture master bytes unchanged; locked song not used) |
| Reopen/reapproval preserved | YES |
| Locked Jay artifact untouched | YES |

## Applicable tests

`py -3.14 -m pytest tests/test_app.py tests/test_approve.py tests/test_review.py tests/test_ingest.py tests/test_transcribe.py tests/test_uncertainty.py tests/test_structure.py tests/test_faster_whisper_candidate.py tests/test_primary_engine.py --ignore=tests/test_parakeet_candidate.py`

Result: 69 passed.

## Source integrity

Locked master SHA-256 remains `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. This ACI did not approve or rewrite that artifact. Fixture `Thanks for watching!` was left in machine text.

## Errors / warnings

Python 3.14 without faster-whisper returns an operator-facing extraction error. `.venv-faster-whisper` (Python 3.12) ran the primary engine on a short fixture WAV (not the locked Jay song) and opened paragraph review in DRAFT. That fixture produced machine text `Thank you.` flagged as uncertain; it was not approved.

## Merge / push

NOT MERGED. NOT PUSHED.

## Recommendation

A2L FRONTEND: **PASS**  
END-TO-END USER WORKFLOW AVAILABLE: **YES**
