# ACI-ATL-004 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-ATL-004 — Lyric structuring  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged; not approved lyrics)

---

## Execution status

COMPLETE on bounded feature branch. Not merged. Not pushed. Next capability not started.

## Branch

`feature/aci-atl-004` (from `feature/aci-atl-003` @ `d427d8e`)

## Current Truth discovered

ACI-001 through ACI-003 PASS. Fixed song unchanged. GVCA/ACICE still not in-repo. No approved lyrics existed. Vocal isolation still absent.

## Implementation summary

`python -m a2l structure <uncertainty_report.json>`

Consumes the ACI-ATL-002 draft and ACI-ATL-003 report. Emits timed `machine_line` rows with original text and flags. Time gaps ≥ 2 s become empty `TIME_GAP` rows. No verse/chorus labels. No LLM rewrite.

## Lyric structure produced

Timed annotated lines plus gap placeholders:

- 32 machine lines (exact uncertainty `preserved_text`)
- 5 `TIME_GAP` rows with empty text
- 25 lines marked uncertain
- `section_label` always `null`
- `usable_as_approved_lyrics` = false

## Files changed

`a2l/structure.py`, CLI, tests, `docs/LYRIC_STRUCTURING.md`, `docs/STRUCTURED_LYRIC_CONTRACT.md`, Nebula ACI/ACR/evidence.

## Dependencies introduced

None.

## Tests performed

`python -m pytest -q` — **39 passed** (ACI-001 through ACI-003 included).

## Fixed-song runtime results

`python scripts/validate_aci_atl_004.py` → **PASS**

Same locked song SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`. Master unchanged. Existing transcription draft reused; uncertainty and structuring re-run.

## Preservation of uncertainty

Structured lines match uncertainty item texts 1:1. Flags including `WHISPER_BOILERPLATE`, `REPEATED_SEGMENT`, `CHUNK_BOUNDARY`, and `NO_SPEECH_LIKELY` remain. Boilerplate `Thanks for watching!` was not rewritten.

## Errors / material issues

None that blocked the ACI. ACICE still missing, so song-form labels were not invented.

## Scope compliance

Lyric structuring only. No human review, approval, approved artifacts, or vocal isolation.

## Architecture / documentation changes

Fourth pipeline stage. Contract: `docs/STRUCTURED_LYRIC_CONTRACT.md`.

## Commit information

`2872e51` on `feature/aci-atl-004` (implementation). Follow-up commit records this SHA in the ACR.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Remaining risks

Human review is still required. Time gaps may reflect chunk/timing artifacts, not true rests. Unverified lines are still not established lyrics.

## Recommendation

**PASS**

---

## Minority Report

1. **No verse/chorus.** A lyric-structure product could guess chorus from repeats (`Play something we can stomp to`). That would be invention. This ACI kept `section_label` null until ACICE or a later human-review ACI defines form.

2. **TIME_GAP heuristic.** Gaps ≥ 2 s are flagged empty. Some gaps may be Whisper timestamp coarseness, not musical silence.

3. **Transcription reuse.** Validation reused the ACI-003 Whisper draft instead of spending another API pass. That matches “consume the existing draft.” A stricter reading would re-transcribe every ACI; that was not done.
