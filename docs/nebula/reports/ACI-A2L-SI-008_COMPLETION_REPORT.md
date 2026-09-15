# ACI-A2L-SI-008 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-008 — Audio Intelligence classification resolution  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **ENGINE #3 PARTIAL PASS**. MUSICAL VALIDATION is **PENDING JAY**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch. CONTROL reproduced SI-007. Equivalent richer prompts, a 3-template ensemble, bare labels, and per-window mean cosine were compared on the locked Jay master. Energy / Intensity was not reopened. SI-007 evidence hashes were unchanged. No new CLAP weights. No cloud. No GPU.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-008-audio-classification-resolution` |
| Base | SI-007 `feature/aci-a2l-si-007-audio-intelligence` @ `6e94bad` |
| Implementation | recorded after commit |

## Engine

| Field | Value |
| --- | --- |
| Checkpoint | `laion/larger_clap_music` `a0b4534a14f58e20944452dff00a22a06ce629d1` |
| Packages | transformers 4.44.2, torch 2.14.0+cpu |
| Control | EOS text, mean-pooled 10s audio, SI-007 templates, cosine ranking |
| Resolution rule | highest `top_margin` per category; not a preferred label |
| Download | NO |
| Cloud | NO |
| Device | cpu |

## Laptop evidence

| Item | Observed |
| --- | --- |
| Analysis wall-clock | 16.44 s |
| Peak working set | 968.1 MB |
| vs SI-007 | 16.95 s / 1061.0 MB |
| GPU required | NO |
| Additional download | NO |

## Diagnostic answer

| Cause | Evidence |
| --- | --- |
| A formulation | Ensemble/bare can change winners and lift `top_margin` slightly. Not enough for instrumentation or genre WIN. |
| B embedding | Pooler mean pairwise cosine ~0.999 (collapsed). EOS control ~0.80–0.86 (usable). EOS path retained. |
| C scoring | Softmax remains flat. Cosine `top_margin` / `spread` are the reported metrics. |
| D aggregation | Window-mean `top_margin` ≈ CONTROL mean-pool. Whole-song pooling did not destroy the signal. |
| E unsuitability | Unique-label instrumentation and genre remain STILL WEAK on this checkpoint/song. |

## Category results (exact)

Thresholds: WIN if `top_margin` ≥ 0.015; PARTIAL if ≥ 0.008 or spread gain ≥ 0.020; else NO WIN.

See `classification_resolution_readable.txt` for full ranked lists.

### Instrumentation — NO WIN

CONTROL top_margin=0.0003 spread=0.0655 (Drums 0.0411 / Piano 0.0408)  
RESOLUTION ensemble top_margin=0.0042 spread=0.0241 (Synthesizer 0.0263 / Organ 0.0220)  
ASSESSMENT: STILL WEAK

### Genre / Style — NO WIN

CONTROL top_margin=0.0004 spread=0.0391 (Pop 0.0456 / Country 0.0452)  
RESOLUTION bare top_margin=0.0015 spread=0.0400 (Country Rock 0.0483 / Roots Rock 0.0467)  
ASSESSMENT: STILL WEAK

### Vocal Characteristics — PARTIAL

CONTROL top_margin=0.0006 spread=0.0439 (Female 0.0210 / Male 0.0204)  
RESOLUTION ensemble top_margin=0.0083 spread=0.0252 (Predominantly Instrumental 0.0266 / Prominent Lead Vocal 0.0183)  
ASSESSMENT: USEFUL (margin only; musical fit is Jay)

### Acoustic / Electronic — WIN

CONTROL = RESOLUTION (`{label} music`)  
top_margin=0.0292 spread=0.0404 (Mixed Acoustic/electric 0.0187 / Electronic/synth-heavy -0.0105)  
ASSESSMENT: USEFUL

## ENGINE #3 RESULT

PARTIAL PASS

Useful CLAP capability now: Energy / Intensity (SI-007, not reopened) + Acoustic/Electronic (CONTROL) + Vocal PARTIAL. Instrumentation and genre remain unresolved unique-label classifications. CLAP was not replaced.

MUSICAL VALIDATION: PENDING JAY

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **172 passed** (165 SI-007 baseline + 7 SI-008 isolation tests).

---

## Minority Report

WHAT IS BEING DONE: Resolution is chosen by `top_margin`, so instrumentation ensemble ranks Synthesizer first. CONTROL's larger two-cluster spread (0.065) was not selected.  
WHY IT MATTERS: Discriminating a unique winner is not the same as preserving a high/low cluster.  
PA IMPACT: Jay musical review; instrumentation remains NO WIN.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Vocal ensemble ranks Predominantly Instrumental above lead-vocal labels. Results were not rewritten toward a sung mix.  
WHY IT MATTERS: PARTIAL is discrimination, not singer-identity truth.  
PA IMPACT: Jay musical review.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Hugging Face `ClapTextPooler` remains collapsed (~0.999 pairwise) and was not used as RESOLUTION.  
WHY IT MATTERS: Confirms SI-007 EOS decision.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL
