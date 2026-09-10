# ACI-A2L-005 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-005 — faster-whisper large-v3 transcription test  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **EXECUTION COMPLETE** (feature branch; not merged). Lyric quality is **not** a CAE PASS.

---

## Execution status

COMPLETE on bounded feature branch. Not merged. Not pushed. Parakeet deferred. No other candidate executed.

## Branch

`feature/aci-a2l-005-faster-whisper-large-v3`  
**Base:** `feature/aci-atl-004` @ `35c636f023bcf2e00b7bb9f6bfe06d703661d452`

Did not branch from `feature/aci-a2l-005-parakeet`.

## Current Truth discovered

ACI-001 through ACI-004 remain the validated A2L path (whisper-1). NVIDIA NeMo / Parakeet was interrupted on a prior branch and was not continued. No NVIDIA GPU is visible on this workstation.

## Implementation summary

Isolated script:

`python scripts/run_faster_whisper_candidate.py`

Uses isolated `.venv-faster-whisper` (Python 3.12.10). Does not change `a2l.transcribe` or overwrite `artifacts/ingest/<sha>/machine_transcription/`.

## Engine record

| Field | Value |
| --- | --- |
| Engine | faster-whisper 1.2.1 |
| CTranslate2 | 4.8.2 |
| Model | `large-v3` |
| Model repo | `Systran/faster-whisper-large-v3` |
| Device | cpu |
| Compute type | int8 |
| CPU threads | 8 |
| Language | en (album-language assumption; not a lyric rewrite) |
| Beam size | 5 |
| Temperature | 0.0 |
| Word timestamps | true |
| VAD | off |
| condition_on_previous_text | false |
| Model load | 11.60 s |
| Processing | 112.79 s |
| Audio duration processed | 207.1211875 s (matches locked master) |
| Segments | 40 |

## Dependencies introduced (isolated venv only)

faster-whisper==1.2.1, ctranslate2==4.8.2, huggingface-hub==1.31.0, tokenizers==0.23.2, onnxruntime==1.30.0, av==18.1.0, numpy==2.5.3, plus their declared transitive deps. Not added to the main A2L package.

## Tests performed

`py -3.14 -m pytest tests/test_ingest.py tests/test_transcribe.py tests/test_uncertainty.py tests/test_structure.py tests/test_faster_whisper_candidate.py -q` — **44 passed** (39 existing A2L tests + 5 isolation tests). Untracked Parakeet test file was not collected.

## Fixed-song runtime results

Locked SHA-256 unchanged: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.  
whisper-1 `transcription_draft.json` SHA-256 unchanged: `82ca9474e3cc0179ffdb6e7948df081c4785cd29f0e9a7526d3d318525055471`.  
Original master not modified. No vocal isolation. No LLM repair.

## Errors / material issues

None that blocked execution. HuggingFace CDN download of `model.bin` (3,087,284,237 bytes) took ~41 minutes on library network; transcription itself was ~2 minutes after the model was local.

## Scope compliance

faster-whisper / large-v3 only. Parakeet not continued. No uncertainty, structuring, UI, review, or approval.

## Merge / push status

**NOT MERGED. NOT PUSHED.**

## Recommendation

**EXECUTION COMPLETE.** Operator determines whether the transcription is accurate enough for A2L.

---

## Minority Report

1. **Quality is not CAE's call.** The model ran and preserved actual machine text, including likely Whisper-family boilerplate (`Thanks for watching!`) and repeated outro lines (`Play something we can start to`). Those were not rewritten.

2. **CPU int8, not GPU.** Best available on this machine. A later CUDA box could change speed and possibly numeric output; this artifact is the CPU/int8 result.

3. **Parakeet WIP is off this branch.** Uncommitted Parakeet files were left untracked and not committed here. The Parakeet ACI text was copied to `%USERPROFILE%\.cache\a2l-parakeet-wip-aci-a2l-005` so this ACI number could be used for faster-whisper without destroying that draft.

4. **language=en** is an assumption about the locked English album master, not invented lyrics. Auto-detect was not used.

5. **Not the A2L engine.** This candidate is not wired into ingest → transcribe → uncertainty → structure.
