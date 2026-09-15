# ACI-A2L-SI-009 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-009 — Instrumentation & genre resolution candidate  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **ENGINE #3 PARTIAL PASS**. Genre / Style is an Engineering WIN. Instrumentation remains NO WIN. MUSICAL VALIDATION is **PENDING JAY**. Repair Attempt 3 remains available and was not started. Not merged.

---

## Execution status

COMPLETE on bounded feature branch against the APPROVED ACI. ONE specialized pretrained music tagger (Audio Spectrogram Transformer / AudioSet) was run on the locked Jay master. CLAP was not retuned and was not replaced. Energy / Intensity, Acoustic / Electronic, and Vocal Characteristics were not reopened. No Song Intelligence Record was created.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-009-instrumentation-genre-resolution` |
| Base | SI-008 `feature/aci-a2l-si-008-audio-classification-resolution` @ `1b61291` |
| Implementation | `fd41713` |

## Candidate

| Field | Value |
| --- | --- |
| Candidate | Hugging Face `transformers` `ASTForAudioClassification` |
| Checkpoint | `MIT/ast-finetuned-audioset-10-10-0.4593` |
| Revision | `f826b80d28226b62986cc218e5cec390b1096902` |
| Packages | transformers 4.44.2, torch 2.14.0+cpu, librosa 1.0.0, huggingface_hub 0.36.2 |
| Software license | Apache-2.0 (transformers, huggingface_hub); BSD-style (torch); ISC (librosa) |
| Model license | bsd-3-clause (Hugging Face card; original AST repo BSD 3-Clause, Yuan Gong 2021) |
| Commercial license gate | PASS |
| Sidecar | `.venv-clap` reused (Python 3.12.10); not installed into A2L 3.14 |
| Cache | `%USERPROFILE%\.cache\a2l-ast` (346.4 MB) |
| Device | cpu |
| GPU required | NO |
| Cloud required | NO |
| Download | YES — first-time `model.safetensors` 346,404,948 bytes |

## Locked master

| Field | Value |
| --- | --- |
| Path | `01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 before/after | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Master input | PASS |
| Master hash unchanged | YES |
| Source preprocessing | in-memory librosa 16 kHz mono float32; 21 × 10.24 s AST chunks; source not overwritten |

## Laptop evidence

| Item | Observed |
| --- | --- |
| Analysis wall-clock | 118.56 s |
| Inference wall-clock | 87.46 s |
| Peak working set | 698.3 MB |
| Model / cache size | 346.4 MB |
| Environment size | `.venv-clap` 1,175,776,203 bytes (reused; no second torch install) |
| GPU required | NO |
| Cloud required | NO |
| OOM / crash | none |

## Category results (exact)

Thresholds were committed before seeing audio: WIN if `top_margin` ≥ 0.05, or ≥1 strong tag (sigmoid ≥ 0.15) with spread ≥ 0.10, or a multi-label cluster (≥2 strong and ≥ half of labels weak). PARTIAL if margin ≥ 0.02 or ≥1 strong tag. Scores are model-native sigmoid values, not calibrated probabilities.

See `instrumentation_genre_readable.txt` for full native lists.

### Instrumentation — NO WIN

Guitar 0.0654 / Plucked string instrument 0.0512  
top_margin=0.0142 spread=0.0654 strong_count=0  
Groups (max of members): guitar_family 0.0654, drums_percussion 0.0092, synthesizer_electronic 0.0028, keyboard_piano_organ 0.0012  
ASSESSMENT: STILL WEAK

Native evidence was produced and is more ordered than SI-008 CLAP (guitar-led; synthesizer 0.0004). It did not meet the precommitted discrimination thresholds. Thresholds were not moved after seeing the song.

### Genre / Style — WIN

Grunge 0.1673 / Independent music 0.1099  
Rock and roll 0.0833, Rock music 0.0790, Progressive rock 0.0595, Country 0.0554  
top_margin=0.0573 spread=0.1671 strong_count=1 (Grunge)  
ASSESSMENT: USEFUL

Musical fit of Grunge vs country/rock remains Jay. Engineering WIN does not convert the tag into an authoritative song fact.

## Comparison to CLAP (preserved SI-008; not rerun)

| Category | CLAP SI-008 | AST SI-009 |
| --- | --- | --- |
| Instrumentation | NO WIN; ensemble Synthesizer 0.0263 / Organ 0.0220; margin 0.0042 | NO WIN; Guitar 0.0654 / Plucked string 0.0512; margin 0.0142 |
| Genre / Style | NO WIN; bare Country Rock 0.0483 / Roots Rock 0.0467; margin 0.0015 | WIN; Grunge 0.1673 / Independent music 0.1099; margin 0.0573 |

CLAP Energy / Acoustic / Vocal were not replaced.

## ENGINE #3 RESULT

PARTIAL PASS

Audio Intelligence composition after this ACI:

- Energy / Intensity: CLAP + deterministic measurement — WIN (SI-007; not reopened)
- Acoustic / Electronic: CLAP — WIN (SI-008 CONTROL; not reopened)
- Vocal Characteristics: CLAP — PARTIAL (not reopened)
- Instrumentation: Specialized Analyzer — NO WIN
- Genre / Style: Specialized Analyzer — WIN

Unresolved after Repair Attempt 2 of 3: **Instrumentation**. Repair Attempt 3 remains available and was not started.

MUSICAL VALIDATION: PENDING JAY

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **181 passed** (172 SI-008 baseline + 9 SI-009 isolation tests).

---

## Minority Report

WHAT IS BEING DONE: Reused the SI-007 `.venv-clap` CPU torch/transformers sidecar instead of creating a second ~1 GB venv.  
WHY IT MATTERS: Laptop practicality; AST added no new packages.  
PA IMPACT: Environment dependency on `.venv-clap`.  
DISPOSITION: NON-BLOCKING

WHAT IS BEING DONE: Inherited `HF_HUB_OFFLINE=1` from the prior CLAP session was cleared so the first AST weight fetch could run.  
WHY IT MATTERS: Hub is weight distribution, not cloud inference. First run required a 346 MB download.  
PA IMPACT: First-run network dependency; later runs can be local.  
DISPOSITION: NON-BLOCKING

WHAT IS BEING DONE: AudioSet ontology is CC BY-SA 4.0; this run emits native class names and does not adapt the ontology. Checkpoint license is BSD-3-Clause.  
WHY IT MATTERS: License was not inferred from the transformers Apache-2.0 library license.  
PA IMPACT: Attribution for AudioSet names if tags are later shown in product UI.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Instrumentation ranking is guitar-led and more ordered than CLAP, but engineering result remains NO WIN under precommitted thresholds. Thresholds were not retuned after seeing audio.  
WHY IT MATTERS: Avoids converting a weakly scored tag into a false WIN.  
PA IMPACT: Repair Attempt 3 remains available for instrumentation.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Genre winner is Grunge, not Country / Country Rock. Results were not rewritten toward Jay's identity or prior CLAP rankings.  
WHY IT MATTERS: Engineering WIN is discrimination, not promotional genre truth.  
PA IMPACT: Jay musical review.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: transformers emitted a mel-filter warning (`num_mel_filters` 128 vs `num_frequency_bins` 256). Native AST preprocessor config was not changed.  
WHY IT MATTERS: Warning is checkpoint/extractor behavior, not a source mutation.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL
