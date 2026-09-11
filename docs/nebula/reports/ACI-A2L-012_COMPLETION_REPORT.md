# ACI-A2L-012 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-012 — NVIDIA Parakeet A2L workflow integration  
**AIW:** CAE  
**Date:** 2026-09-10  
**Recommendation:** **READY FOR PARAKEET A2L WORKFLOW REVIEW** (feature branch; not merged; quality winner not decided)

---

## Execution status

COMPLETE on bounded feature branch through Operator-reviewable UI. NVIDIA Parakeet is a selectable alternate engine. Faster-whisper remains the default/primary path. CAE did not approve Parakeet lyrics and did not decide which engine wins.

Not merged. Not pushed.

## Branch

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-012-nvidia-workflow` |
| Base | `feature/aci-a2l-011-nvidia-candidate` @ `465438b` |

## Workflow

```text
Upload WAV + engine selection (before transcription)
  → ingest (CONTROL A; original WAV not rewritten)
  → NVIDIA Parakeet TDT 0.6B v2  (or faster-whisper / large-v3)
  → uncertainty (flag; do not invent confidence Parakeet does not provide)
  → lyric structuring
  → paragraph review / correction / save (not approval)
  → explicit approve (not performed for Parakeet in this ACI)
```

Parakeet writes `a2l_pipeline_parakeet/`. Primary `a2l_pipeline/` is untouched.

## Locked-song live check

| Check | Result |
| --- | --- |
| App loads | PASS — http://127.0.0.1:8781/ |
| Engine selector | PASS — NVIDIA PARAKEET / TDT-0.6B-V2 |
| Locked WAV processed | PASS |
| Original WAV SHA | unchanged `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Parakeet transcription | PASS — 86.21 s CPU |
| Structuring / review UI | PASS — 46 lines, lyric state DRAFT, NOT_APPROVED |
| Uncertainty | conservative — `NO_ENGINE_CONFIDENCE` recorded, not mapped to Whisper logprob |
| Save ≠ approve / explicit approve required | unchanged; Parakeet not approved |
| Provenance | `nvidia_nemo_parakeet` / `parakeet-tdt-0.6b-v2` |
| Faster-whisper artifacts | unchanged |
| Regression tests | PASS (`python -m pytest tests --ignore=tests/test_parakeet_candidate.py`) |

## Out of scope honored

No primary promotion, no faster-whisper removal, no frontend redesign, no vocal isolation, no LLM correction, no additional engine, no merge/push.
