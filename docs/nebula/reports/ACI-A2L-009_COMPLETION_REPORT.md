# ACI-A2L-009 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-009 — Real-song end-to-end validation  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **PARTIAL PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. Phase 1 prepared review. Operator explicitly approved. Phase 2 validated artifacts without modifying approved lyrics. Not merged. Not pushed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-009-real-song-validation` |
| Base | `feature/aci-a2l-008-approved-lyrics` @ `e122b7a51f932e773fa4332e840fc1296c5e7fff` |

## Complete pipeline validation result

```text
WAV → INGEST → FASTER-WHISPER / WHISPER LARGE-V3 → UNCERTAINTY
  → LYRIC STRUCTURING → HUMAN REVIEW / CORRECTION
  → EXPLICIT OPERATOR APPROVAL → APPROVED LYRIC ARTIFACT
```

Existing primary-path artifacts under `a2l_pipeline/` were reused. Transcription was not rerun. No candidate-specific copying was required.

| Check | Result |
| --- | --- |
| Locked song state APPROVED | YES |
| approved_lyrics.txt exists | YES |
| approved_lyrics.json exists | YES |
| TXT is clean of clocks/flags/MACHINE labels/confidence | YES |
| JSON provenance present | YES |
| Machine transcription preserved separately | YES (usable_as_approved_lyrics false; SHA unchanged vs ACI-007) |
| Human-review provenance preserved separately | YES (machine_text retained; 3 HUMAN_CORRECTED lines) |
| Original WAV unchanged | YES |
| APPROVED persists after reload | YES (`GET /api/state` lyric_state=APPROVED) |

## Primary transcription engine

faster-whisper / Whisper large-v3 (`Systran/faster-whisper-large-v3`), CPU int8, faster-whisper 1.2.1, CTranslate2 4.8.2. `python -m a2l transcribe` was not changed.

## Source SHA verification

- Locked master: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- Ingest `authoritative_source/source.wav`: same
- whisper-1 JSON: `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`
- whisper-1 TXT: `c05fc1227ad6842bb4efa9cf1c375bd392c5fe5361e5a9ad6d49e22864147886`
- Primary transcription JSON: `3c645aeddce7b7df29e8ce93653c273de3dc1f2e561f33a16af5f3a8cacb0919` (unchanged vs ACI-007)

## Human correction count

**3** (unchanged from Phase 1; no additional `/api/save` before `/api/approve`)

- L27 `stall` → `stomp`
- L36 `Hunkers` → `Hook us`
- L40 `start` → `stomp`

## Uncertainty information

Uncertainty report: 7 questionable, 33 unverified machine-text, 40 segments.  
Review: 12 uncertain lines including 5 TIME_GAP rows. Structured draft: 40 machine lines, 5 time gaps.

## Approved artifact paths

```text
C:\Users\tim\Documents\business_related\The_AI_Guy\nebula\2 - TAIG2K_SOFTWARE\audio_2_lyrics_a2l\artifacts\ingest\bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be\a2l_pipeline\approved_lyrics\approved_lyrics.txt
C:\Users\tim\Documents\business_related\The_AI_Guy\nebula\2 - TAIG2K_SOFTWARE\audio_2_lyrics_a2l\artifacts\ingest\bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be\a2l_pipeline\approved_lyrics\approved_lyrics.json
```

TXT SHA-256: `8da23213e2d0b3fb62ae84a9d059b026117baf793e8cacbfc61db857ad2f476c`  
JSON SHA-256: `7ac68495aca44d35b44ab555d86472894292f092116bdbca2c2ee0154ecb29d6`

Approval event: `approved_by=OPERATOR`, `method=EXPLICIT_CONFIRM`, `automatic=false`, `approved_at=2026-09-10T23:24:59.039288+00:00`. JSON `source_sha256` matches the locked SHA. Engine recorded as faster-whisper / large-v3. Approved text in JSON equals the TXT body.

## Regression test results

`py -3.14 -m pytest tests/test_ingest.py tests/test_transcribe.py tests/test_uncertainty.py tests/test_structure.py tests/test_faster_whisper_candidate.py tests/test_review.py tests/test_primary_engine.py tests/test_approve.py --ignore=tests/test_parakeet_candidate.py`

**63 passed.** `test_locked_song_is_operator_approved` now asserts the Operator-approved locked-song artifacts.

## Effort evidence (not invented)

| Item | Available evidence |
| --- | --- |
| Machine lyric spans | 40 machine lines (+ 5 time gaps) |
| Human corrections | 3 of 40 machine lines |
| Unresolved uncertainty | 7 questionable; 12 review uncertain lines |
| Transcription processing time | ACI-A2L-005 recorded 112.79 s processing + 11.60 s model load; not remeasured here |
| Previously Operator-established quality | Three chorus-word corrections (stall/Hunkers/start) from ACI-006/007 |
| Workflow | Paragraph review UI; Save vs explicit Approve; no candidate copy |
| Material failures | None that blocked the path. Prior 8765 server was restarted so `/api/approve` loaded |

Operator judges whether that is materially less work than transcribing from scratch.

## Errors / warnings

None that blocked validation. Approved TXT still contains leftover machine lines flagged below. CAE did not edit them.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Recommendation

**PARTIAL PASS.** The established pipeline produced Operator-approved TXT/JSON from the locked master with provenance preserved. The authoritative lyric body still includes previously flagged machine leftovers that were not corrected before Approve.

---

REAL LOCKED SONG: **APPROVED**

END-TO-END A2L VALIDATION: **PARTIAL PASS**

---

## Minority Report

1. The approved TXT still ends with `Thanks for watching!` (`WHISPER_BOILERPLATE`). That is not a song lyric. The Operator approved it. CAE did not delete it.

2. Three approved lines still read `Play something we can start to` after L40 was corrected to `stomp to`. Same machine phrase, uncorrected copies.

3. First-chorus `We can't hear the dance and get a little bored loose` sits beside later `We came here to dance and get a little footloose`. FLAG as internal inconsistency; no rewrite.

4. Human correction count stayed at 3. Server log shows `POST /api/approve` without a new `POST /api/save` in this checkpoint.

5. Review JSON `authority` remains `NON_AUTHORITATIVE_REVIEWED_DRAFT` while `approval_status` is `APPROVED`. Authoritative lyrics are the approved_lyrics files.

6. Processing time was inherited from ACI-A2L-005, not measured again on the 007 primary write.
