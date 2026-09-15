# ACI-A2L-SI-007 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-007 — Audio Intelligence engine candidate validation  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **PASS** on feature branch. ENGINEERING WIN is **YES**. MUSICAL VALIDATION is **PENDING JAY**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch against the APPROVED ACI. Isolated sidecar `.venv-clap` (Python 3.12.10) ran `transformers` `ClapModel` on `laion/larger_clap_music` against the locked Jay master on CPU. Incomplete SI-005 snapshot weights were deleted and replaced by a hardlink to the complete local blob. No cloud inference. Source audio and approved lyrics were not modified. No Song Intelligence Record was created. Rhythm/Structure, Key/Mode, and Lyric Intelligence were not reopened.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-007-audio-intelligence` |
| Base | SI-006 `feature/aci-a2l-si-006-lyric-intelligence` @ `e5efb38` |
| Implementation | recorded after commit |

## Engine

| Field | Value |
| --- | --- |
| Method | mean-pooled 10s CLAP audio embeddings; EOS-token text projection; RMS/onset energy |
| Packages | transformers 4.44.2, torch 2.14.0+cpu, librosa 1.0.0, huggingface_hub 0.36.2 |
| Checkpoint | `laion/larger_clap_music` |
| Revision | `a0b4534a14f58e20944452dff00a22a06ce629d1` |
| Model source | https://huggingface.co/laion/larger_clap_music/tree/a0b4534a14f58e20944452dff00a22a06ce629d1 |
| License | Apache-2.0 |
| Python | 3.12.10 sidecar (`.venv-clap`); not installed into A2L 3.14 |
| Device | cpu |
| Download | no new CLAP weights; complete 776,444,665-byte blob reused |
| Cloud | NO |

## Master input

| Field | Value |
| --- | --- |
| Path | Desktop Jay masters `01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 before/after | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Ingest source SHA-256 | unchanged, same digest |
| Protected artifacts | unchanged |

CONTROL A audio was hashed, not remastered, not overwritten.

## Laptop evidence (observed)

| Item | Observed |
| --- | --- |
| GPU required | NO |
| Cloud required | NO |
| Download required | NO new CLAP weights; transformers 4.44.2 pip pin (~9.5 MB) this session |
| Analysis wall-clock | 16.95 s |
| Peak working set | 1061.0 MB |
| Model blob | 776,444,665 bytes (740.5 MiB) |
| Isolated HF cache | 1,557,087,032 bytes (~1.45 GB) |
| Sidecar venv | 1,175,776,203 bytes (~1.10 GB) |
| CPU | Intel i7-1195G7 class (Family 6 Model 140) |
| OOM / crash | none |

## Machine-derived output (exact)

Do not rewrite rankings because another label seems more musical.

```text
INSTRUMENTATION
1. Drums                        cosine=0.0411  softmax=0.0796
2. Piano                        cosine=0.0408  softmax=0.0796
3. Percussion                   cosine=0.0408  softmax=0.0796
4. Violin                       cosine=0.0406  softmax=0.0796
5. Keyboard                     cosine=0.0406  softmax=0.0796
6. Organ                        cosine=0.0401  softmax=0.0796
7. Synthesizer                  cosine=-0.0209  softmax=0.0747
8. Banjo                        cosine=-0.0211  softmax=0.0747
9. Bass Guitar                  cosine=-0.0215  softmax=0.0747
10. Electric Guitar              cosine=-0.0217  softmax=0.0747
11. Acoustic Guitar              cosine=-0.0217  softmax=0.0747
12. Fiddle                       cosine=-0.0227  softmax=0.0746
13. Harmonica                    cosine=-0.0244  softmax=0.0744

GENRE / STYLE
1. Pop                          cosine=0.0456  softmax=0.1132
2. Country                      cosine=0.0452  softmax=0.1131
3. Rock                         cosine=0.0441  softmax=0.1130
4. Americana                    cosine=0.0405  softmax=0.1126
5. Southern Rock                cosine=0.0398  softmax=0.1125
6. Country Rock                 cosine=0.0092  softmax=0.1090
7. Roots Rock                   cosine=0.0079  softmax=0.1089
8. Funk                         cosine=0.0077  softmax=0.1089
9. Blues                        cosine=0.0065  softmax=0.1087

VOCAL CHARACTERISTICS
1. Female Lead Vocal            cosine=0.0210  softmax=0.1704
2. Male Lead Vocal              cosine=0.0204  softmax=0.1703
3. Prominent Lead Vocal         cosine=0.0195  softmax=0.1702
4. Predominantly Instrumental   cosine=-0.0212  softmax=0.1632
5. Vocals Present               cosine=-0.0228  softmax=0.1629
6. Backing Vocals               cosine=-0.0229  softmax=0.1629

ACOUSTIC / ELECTRONIC CHARACTER
1. Mixed Acoustic/electric      cosine=0.0187  softmax=0.2571
2. Electronic/synth-heavy       cosine=-0.0105  softmax=0.2495
3. Predominantly Acoustic       cosine=-0.0217  softmax=0.2467
4. Predominantly Electric       cosine=-0.0218  softmax=0.2467

ENERGY / INTENSITY
MEASURED rms_mean: 0.23789680004119873
MEASURED rms_peak: 0.4968408942222595
MEASURED onset_count: 1047
MEASURED onset_density_per_second: 5.055011065380597
MACHINE-DERIVED label: HIGH ENERGY
rule: HIGH ENERGY if rms_mean>=0.15; MEDIUM ENERGY if rms_mean>=0.08; else LOW ENERGY. Not a loudness or mastering/QC judgment.
```

## Authority

MASTER WAV: AUTHORITATIVE INPUT  
ENERGY RMS / ONSET: MEASURED  
ENERGY LABEL: MACHINE-DERIVED  
INSTRUMENTATION / GENRE / VOCAL / ACOUSTIC-ELECTRONIC: MACHINE-DERIVED  
SONG INTELLIGENCE RECORD: not created  
OPERATOR / JAY REVIEW REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **165 passed** (Python 3.14.3; 153 SI-006 baseline + 12 SI-007 isolation tests). Parked Parakeet helpers remain ignored.

## ENGINEERING WIN

YES

MUSICAL VALIDATION: PENDING JAY

---

## Minority Report

WHAT IS BEING DONE: Hugging Face `ClapTextPooler` (first-token tanh) collapsed all text labels to ~0.999 cosine. Execution uses LAION EOS-token hidden state + `text_projection`.  
WHY IT MATTERS: Without this, rankings were numerical noise, not Audio Intelligence.  
PA IMPACT: NONE for engineering; pooling choice is recorded, not a silent vocab tune.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: transformers sidecar pinned to 4.44.2 (checkpoint-era API: `audios=`). transformers 5.17 required `audio=` and still collapsed under the HF pooler.  
WHY IT MATTERS: Documents the commercially acceptable runtime actually used.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Incomplete SI-005 `pytorch_model.bin` snapshot (146,305,024 bytes) was deleted. Complete blob 776,444,665 bytes (ETag `5c289311…`) was hardlinked into the snapshot.  
WHY IT MATTERS: ACI forbids treating incomplete cache as valid.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Within-category softmax stays nearly flat because `logit_scale_a.exp()` ≈ 1.028. Ranking uses cosine_similarity, not softmax.  
WHY IT MATTERS: Softmax must not be read as confidence or probability.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Female vs male lead vocal is a near-tie (0.0210 vs 0.0204). `vocals present` ranks below `predominantly instrumental`. Results were not rewritten.  
WHY IT MATTERS: Vocal characterization is MACHINE-DERIVED and may be musically wrong.  
PA IMPACT: Jay musical review.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Instrumentation ranks drums/piano/violin above guitars. That may not match a guitar-forward mix. Engine truth preserved.  
WHY IT MATTERS: ENGINEERING WIN is not musical agreement.  
PA IMPACT: Jay musical review.  
DISPOSITION: INFORMATIONAL
