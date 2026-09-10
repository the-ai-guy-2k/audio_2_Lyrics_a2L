# ACI-A2L-008 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-008 — Approved lyric artifact  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged; locked song not approved)

---

## Execution status

COMPLETE on bounded feature branch. Not merged. Not pushed. The locked Jay song was not approved.

## Branch

`feature/aci-a2l-008-approved-lyrics`  
**Base:** `feature/aci-a2l-007-primary-faster-whisper` @ `d0b0983884889bf6e2b6c602362187f8a0a44c7a`

## Implementation summary

`approve_reviewed_lyrics(..., confirm=True)` is the only writer of approved lyric artifacts. `confirm is not True` raises `APPROVAL_NOT_EXPLICIT` and writes nothing. Save continues to force `NOT_APPROVED`.

The local review UI shows `LYRIC STATE: DRAFT | REVIEWED | APPROVED`, keeps Save as a non-approving action, and requires a browser confirm plus `POST /api/approve` `{ "confirm": true }`.

## Authority / state model

| State | Meaning |
| --- | --- |
| DRAFT | Review object exists in memory; no saved review file |
| REVIEWED | Saved `reviewed_lyric_draft.json`; not approved |
| APPROVED | Review flags plus both `approved_lyrics.txt` and `approved_lyrics.json` |

Machine draft, uncertainty, structured draft, and saved review never auto-approve.

## Explicit approval mechanism

Operator clicks **Mark lyrics APPROVED**, confirms the dialog, UI sends JSON boolean `true`. Function name is `approve_reviewed_lyrics` (not package-root `approve_lyrics`).

## Approved artifact format

- `approved_lyrics.txt` — clean `human_text` lines; no clocks, flags, UNCERTAIN/MACHINE labels
- `approved_lyrics.json` — `AUTHORITATIVE_APPROVED_LYRICS` with source SHA, engine, approval event, approved text

Locations after a real approval:

```text
artifacts/ingest/<sha>/a2l_pipeline/approved_lyrics/
  approved_lyrics.txt
  approved_lyrics.json
```

## Automated validation method

Fixture SHA `aci-a2l-008-fixture` under a temp ingest root. `tests/test_approve.py` proves save does not approve, `confirm=False` is refused, explicit confirm writes clean artifacts, machine_text remains, post-approval save is refused, and the locked song helper stays unapproved.

## Tests performed

`py -3.14 -m pytest tests/test_ingest.py tests/test_transcribe.py tests/test_uncertainty.py tests/test_structure.py tests/test_faster_whisper_candidate.py tests/test_review.py tests/test_primary_engine.py tests/test_approve.py --ignore=tests/test_parakeet_candidate.py`

**63 passed.**

Locked-song UI Approve was **not** clicked.

## Fixed-song validation

Source SHA-256 unchanged: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.  
whisper-1 `transcription_draft.json` SHA-256 unchanged: `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`.  
whisper-1 `transcription_draft.txt` SHA-256 unchanged: `c05fc1227ad6842bb4efa9cf1c375bd392c5fe5361e5a9ad6d49e22864147886`.

Known human corrections remain on the unapproved review (L27 stall→stomp, L36 Hunkers→Hook us, L40 start→stomp).

## Errors / warnings

None that blocked the ACI.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Recommendation

**PASS** for the approval capability. Not a lyric-quality PASS for the locked song.

---

REAL LOCKED SONG APPROVAL STATE: **NOT APPROVED**

APPROVED LYRIC TXT LOCATION: **NOT CREATED**

APPROVED LYRIC JSON LOCATION: **NOT CREATED**

---

## Minority Report

1. The locked song still contains remaining machine errors, including `Thanks for watching!`. Approving it to prove the button would have created false authoritative lyrics. Fixture approval was the correct proof.

2. `confirm` must be JSON boolean `true`. A string `"true"` is rejected. That is intentional.

3. There is no standalone `python -m a2l approve` command. Approval lives on the review server. That matches the ACI (extend the existing review interface) and leaves a small operator-discovery gap.

4. After APPROVED, the review sidecar TXT still stores machine text and flags. That is history, not the clean lyric body. The clean body is only `approved_lyrics.txt`.

5. Untracked Parakeet WIP was not committed and was ignored in pytest.
