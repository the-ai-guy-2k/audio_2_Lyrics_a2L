# ACI-ATL-003 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-ATL-003 — Uncertainty handling  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PASS** (feature branch; not merged; accuracy not claimed)

---

## Execution status

COMPLETE on bounded feature branch. Not merged. Not pushed. Next capability not started.

## Branch

`feature/aci-atl-003` (from `feature/aci-atl-002` @ `3c09e12`)

## Current Truth discovered

| Fact | Finding |
| --- | --- |
| ACI-ATL-001 / 002 | PASS |
| GVCA-ATL-001 / ACICE-ATL-001 | **Not in repository** |
| Vocal isolation | Still absent; not added |
| Album path | Nested folder `Masters  - 24bit_48hz` under the Operator path |
| Masters | Twelve 24-bit/48 kHz stereo WAVs, all 47–107 MB |

Uncertainty handling was implemented from the approved Operator ACI (FLAG IT — DO NOT INVENT IT). ACICE was not found.

## Fixed test-song identity

| Field | Value |
| --- | --- |
| Filename | `01Stomp to MIX MSTR 24bit_48hz.wav` |
| Path | `C:\Users\tim\Desktop\Jays_stuff\2026_album\Masters - 24bit_48hz\Masters  - 24bit_48hz\01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Format | 24-bit 48 kHz stereo PCM WAV, 207.12 s, 59,968,382 bytes |
| Why this song | First numbered album master (`01`). Not switched. |

Original master SHA-256 and mtime were unchanged after the pipeline.

## Implementation summary

`python -m a2l uncertainty <transcription_draft.json>`

Consumes the ACI-ATL-002 draft. Preserves `engine_text`. Writes `uncertainty/uncertainty_report.json`. Never sets `usable_as_approved_lyrics`. Never produces established lyrics.

24-bit PCM energy is now measured. Whisper payloads over 20 MB are sent as temporary same-format PCM slices (not stored working artifacts, no resample/mixdown/isolation).

## Uncertainty method

Deterministic flags. No LLM rewrite.

- Questionable: low confidence, no-speech, compression hallucination, no-signal, Whisper boilerplate, repeated spans, chunk boundaries
- Unverified: remaining machine text, still not approved
- Established: empty in this ACI

## Files changed

- `a2l/uncertainty.py`, `a2l/signal.py`, `a2l/engines.py`, CLI, errors
- `tests/test_uncertainty.py` plus bounded ingest/transcribe tests
- `docs/UNCERTAINTY.md`, `docs/UNCERTAINTY_CONTRACT.md`, `docs/nebula/FIXED_TEST_SONG.md`
- Nebula ACI/ACR/evidence

## Dependencies introduced

None new. Same optional OpenAI extra as ACI-ATL-002.

## Tests performed

```text
python -m pytest -q
# 34 passed
```

Includes prior ACI-001 and ACI-002 tests.

## Real-song runtime results

`python scripts/validate_aci_atl_003.py` → **PASS**

| Stage | Result |
| --- | --- |
| Ingest | CONTROL A, 24-bit/48 kHz stereo, job_id = song SHA-256 |
| Transcribe | `whisper-1`, chunked_upload 3 slices, `NOT_APPROVED` |
| Uncertainty | `REQUIRES_LATER_RESOLUTION` |
| Accuracy | **not claimed** |

Material observations:

- Engine appended `Thanks for watching!` (classic Whisper hallucination). Flagged `WHISPER_BOILERPLATE`, not rewritten.
- Repeated outro spans flagged `REPEATED_SEGMENT`.
- Chunk boundaries at ~72.8 s and ~145.6 s flagged `CHUNK_BOUNDARY`.
- `NO_SPEECH_LIKELY` also appeared on some lyric-like spans (music mix; Whisper score is noisy).
- `we've got some work we blues to share` and `star on too` vs `stomp to` are suspicious machine readings. Flagged where rules applied; not “corrected.”

## Uncertainty evidence

32 spans: 20 questionable, 12 unverified, 0 established.

Evidence directory: `docs/nebula/artifacts/aci-atl-003-evidence/`

## Errors / material issues

No pipeline failure. Material notes: missing ACICE; 25 MB API limit required chunked PCM upload; Whisper music scores over-flag.

## Scope compliance

Uncertainty handling only. No lyric structuring, human review workflow, approved lyric artifacts, or vocal isolation.

## Architecture / documentation changes

Third stage added. Fixed song locked for later ACIs. Chunked upload documented as engine transport, not CONTROL B.

## Commit information

`73c71aa` on `feature/aci-atl-003` (implementation). Follow-up commit records this SHA in the ACR.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Remaining risks

- CONTROL-A mix transcription remains unreliable without human review.
- Chunk boundaries can split phrases.
- Cloud ASR still sends artist audio to OpenAI.
- Later ACIs must keep this same song.

## Recommendation

**PASS**

---

## Minority Report

1. **ACICE still missing.** A stricter reading would STOP until ACICE-ATL-001 is supplied. Implementation followed the approved Operator ACI text instead.

2. **Chunked upload.** Splitting the 57 MB 24-bit master for the Whisper 25 MB limit is a material engine-transport decision. It does not resample or isolate, and chunks are not stored as working audio. A local Whisper runtime would avoid this. Switching songs was forbidden; every album master exceeds 25 MB.

3. **Over-flagging on music.** `NO_SPEECH_LIKELY` fired on spans that look like lyrics. That is FLAG IT, not invention, but it means “questionable” is not a precision measure of lyric error. Downstream human review must not treat unflagged spans as established.
