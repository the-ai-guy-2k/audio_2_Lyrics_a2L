# ACI-A2L-SI-010 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-010 — Instrumentation final resolution  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **ENGINE #3 PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD**. Instrumentation is PARTIAL, not WIN. Repair budget is **EXHAUSTED**. Defect deferred to the bug-fix lane. MUSICAL VALIDATION is **PENDING JAY**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch against the APPROVED ACI. ONE specialized pretrained instrument-presence tagger (PANNs Cnn14) was run on the locked Jay master. Genre, Energy, Acoustic/Electronic, Vocals, CLAP, and AST were not reopened or retuned. No Song Intelligence Record was created. No fourth repair ACI was started.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-010-instrumentation-final-resolution` |
| Base | SI-009 `feature/aci-a2l-si-009-instrumentation-genre-resolution` @ `627aeb0` |
| Implementation | `85c67c9` |

## Candidate

| Field | Value |
| --- | --- |
| Candidate | PANNs Cnn14 audio tagging / instrument presence |
| Checkpoint | `Cnn14_mAP=0.431.pth` Zenodo 3987831 |
| Packages | torch 2.14.0+cpu, torchlibrosa 0.1.0, librosa 1.0.0 |
| Software license | MIT (audioset_tagging_cnn, torchlibrosa); BSD-style (torch); ISC (librosa) |
| Model license | cc-by-4.0 (Zenodo `metadata.license.id`; not inferred from MIT code alone) |
| Commercial license gate | PASS |
| Sidecar | `.venv-clap` reused (Python 3.12.10) |
| Cache | `%USERPROFILE%\.cache\a2l-panns` (327.4 MB) |
| Device | cpu |
| GPU required | NO |
| Cloud required | NO |
| Download | YES — first-time 327,428,481 bytes, md5 `541141fa2ee191a88f24a3219fff024e` |

## Locked master

| Field | Value |
| --- | --- |
| Path | `01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 before/after | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Master input | PASS |
| Master hash unchanged | YES |
| Preprocessing | in-memory librosa 32 kHz mono float32; 21 × 10 s PANNs chunks; source not overwritten |
| Analysis method | independent multi-label clipwise sigmoid; mean/max across chunks; native AudioSet instrument subset |

## Laptop evidence

| Item | Observed |
| --- | --- |
| Analysis wall-clock | 272.47 s (includes first download) |
| Inference wall-clock | 5.25 s |
| Peak working set | 1120.7 MB |
| Model / cache size | 327.4 MB |
| Environment size | `.venv-clap` 1,175,877,730 bytes |
| GPU required | NO |
| Cloud required | NO |
| OOM / crash | none |
| Laptop-practical | YES (inference 5.25 s; download is first-run only) |

## Instrumentation (exact)

Precommitted PANNs operating point: clipwise_mean ≥ 0.50 for strong presence. Cluster WIN if ≥2 labels ≥ 0.30 and ≥4× the median of the rest. PARTIAL if top1 ≥ 0.20, or top1 ≥ 0.10 and spread ≥ 0.10. These are not the SI-009 AST 0.15 threshold.

See `instrument_presence_readable.txt` for the full native list.

Guitar mean=0.1705 max=0.7221  
Plucked string instrument mean=0.1311 max=0.6417  
Electric guitar mean=0.0433 max=0.3206  
Acoustic guitar mean=0.0341  
Bass guitar mean=0.0262  
Drum kit mean=0.0190  
Piano mean=0.0016  
Synthesizer mean=0.0006  

top_margin=0.0394 spread=0.1705 strong_count=0  
ASSESSMENT: WEAK BUT PRESENT  
INSTRUMENTATION RESULT: **PARTIAL**

## Comparison to AST (preserved SI-009; not rerun)

| | AST SI-009 | PANNs SI-010 |
| --- | --- | --- |
| Result | NO WIN | PARTIAL |
| Top1 | Guitar 0.0654 | Guitar mean 0.1705 / max 0.7221 |
| Top2 | Plucked string 0.0512 | Plucked string mean 0.1311 / max 0.6417 |
| Margin | 0.0142 | 0.0394 |
| Strong count | 0 at AST 0.15 | 0 at PANNs 0.50 |

PANNs raised guitar-led scores and produced window maxima above 0.7, but song-level mean stayed below the precommitted 0.50 operating point. AST 0.15 was not lowered.

## ENGINE #3 FINAL RESULT

PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD

Composition:

- Energy / Intensity: WIN (SI-007; not reopened)
- Acoustic / Electronic: WIN (SI-008; not reopened)
- Genre / Style: WIN (SI-009; not reopened)
- Vocal Characteristics: PARTIAL (SI-008; not reopened)
- Instrumentation: PARTIAL (SI-010; not an Engineering WIN)

Known defect: `docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md`  
Disposition: DEFER TO BUG-FIX LANE  
Must not block continued Song Intelligence development.  
No SI-011 instrumentation repair.

MUSICAL VALIDATION: PENDING JAY  
REPAIR BUDGET: EXHAUSTED  
BUG-FIX DEFERRAL REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **190 passed** (181 SI-009 baseline + 9 SI-010 isolation tests).

---

## Minority Report

WHAT IS BEING DONE: Reused `.venv-clap` and already-present torchlibrosa 0.1.0 rather than a second torch venv.  
WHY IT MATTERS: Laptop practicality.  
PA IMPACT: Environment dependency on `.venv-clap`.  
DISPOSITION: NON-BLOCKING

WHAT IS BEING DONE: Song-level WIN used precommitted clipwise_mean. Guitar clipwise_max is 0.7221 in at least one 10s window. That max was preserved as temporal evidence and was not promoted to WIN after seeing results.  
WHY IT MATTERS: Avoids converting a peaked window into unsupported song-level certainty.  
PA IMPACT: Bug-fix lane may later use temporal occupancy as a separate metric.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: PANNs also emits genre-like AudioSet tags (Grunge 0.1961). Those tags were not used to reopen or rescore Genre / Style.  
WHY IT MATTERS: This ACI is instrumentation-only.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: AudioSet ontology remains CC BY-SA 4.0; native class names are emitted, not adapted. Checkpoint is CC-BY-4.0.  
WHY IT MATTERS: License was not inferred from MIT library code alone.  
PA IMPACT: Attribution if tags are later shown in product UI.  
DISPOSITION: INFORMATIONAL
