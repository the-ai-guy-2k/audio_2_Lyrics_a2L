# ACI-A2L-SI-004 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-004 — Key + Mode engine candidate validation  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **EXECUTED** on feature branch. ENGINE WIN is **PENDING OPERATOR**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch. librosa `chroma_cqt` plus Krumhansl–Schmuckler / Krumhansl–Kessler template correlation analyzed the locked Jay master on CPU in an isolated sidecar. The finished mix was used directly. No source separation. No neural key model. Results are MACHINE-DERIVED. Chords were not estimated. No Song Intelligence Record was created. Authoritative source and governed lyric/release artifacts were not modified.

Not merged. Not pushed. `deployable` / `main` not modified. Audio Intelligence was not started.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-004-key-mode` |
| Base | SI-003 `feature/aci-a2l-si-003-structure-resolution` @ `0a4f256` |
| Implementation | recorded after commit |

## Engine

| Field | Value |
| --- | --- |
| Method | librosa `chroma_cqt` mean vector correlated with Krumhansl–Kessler major/minor profiles |
| Packages | librosa 1.0.0, numpy 2.5.3, scipy 1.18.1, soundfile 0.14.0 |
| License | librosa ISC; numpy/scipy BSD; Krumhansl–Kessler profiles from published literature (Krumhansl & Kessler, 1982) |
| Python | 3.12.10 sidecar `.venv-key-mode` |
| Device | cpu |
| Analysis path | finished stereo mix, mono-summed by librosa |
| Source separation invoked | NO |
| Neural key model | NO |

Rejected: Essentia KeyExtractor (AGPL / NC model concern); madmom neural key recognition (NC pretrained weights).

## Locked master

| Field | Value |
| --- | --- |
| File | `01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 before/after | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Ingest authoritative copy | unchanged, same SHA-256 |
| Working copy | none; librosa loaded the 24-bit master directly |

CONTROL A was not modified. SI-002 and SI-003 evidence hashes were not rewritten.

## Laptop evidence (observed)

| Item | Observed |
| --- | --- |
| Hardware | MSI Modern 14 B11MOU, 11th Gen Intel Core i7-1195G7, ~16 GB RAM, Intel Iris Xe |
| GPU required | NO |
| Cloud required | NO |
| Analysis wall-clock | 26.02 s (`analyze_mix()` / chroma_cqt + scoring) |
| Peak working set | 800.7 MB |
| Model / cache | none (no neural key weights downloaded) |
| Sidecar venv | 413,116,929 bytes (~394.0 MB) |
| OOM / crash | none |
| Application usability during analysis | not measured; analysis completed without crash |
| Major install issues | none; Python 3.12 sidecar; not installed into Python 3.14 |

## Machine-derived output (exact)

Do not correct the key because another value seems more musically plausible.

```text
KEY: A
MODE: major
CONFIDENCE: 0.03561118190641567
SCORE: 0.7640792482309879

ALTERNATE CANDIDATES:
  A major  score=0.7641
  D major  score=0.7173
  A minor  score=0.5502
  F# minor  score=0.5189
  E major  score=0.3376
```

Confidence is `margin_over_runner_up / score_spread` (A major vs D major margin 0.0467 over a 24-key spread). It is a supporting score, not a calibrated probability.

## Authority

OUTPUT AUTHORITY: MACHINE-DERIVED  
SONG INTELLIGENCE RECORD: not created  
CHORDS: not estimated  
OPERATOR REVIEW REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **145 passed** (Python 3.14.3; 139 SI-003 baseline + 6 SI-004 isolation tests). Parked untracked Parakeet helpers remain ignored.

## ENGINE WIN

PENDING OPERATOR

---

## Minority Report

1. **Confidence is weak by construction.** A major (0.764) beats D major (0.717) by a small margin. The estimator did not fail; the mix chroma does not strongly isolate one tonic. Operator may treat this as PASS (useful key+mode on laptop) or PARTIAL PASS (key useful, confidence weak).

2. **Engine truth was not rewritten.** Relative keys (A major / F# minor) and neighboring keys (D major, E major) remain alternates. CAE does not substitute a “more plausible” key.

3. **Whole-mix mean chroma** averages the full 207 s master. Modulation, guitar solos, and mix energy are collapsed into one vector. That is the spike method, not a limitation to paper over.

4. **No neural model, no Demucs, no Essentia.** Licensing is commercially acceptable for this candidate. Sidecar venv (~394 MB) is practical vs the ~1.07 GB All-In-One sidecar.

5. **Quality is Operator's call.** CAE does not declare KEY + MODE WIN.
