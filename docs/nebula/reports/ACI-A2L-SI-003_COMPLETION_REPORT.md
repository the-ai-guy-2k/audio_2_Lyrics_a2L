# ACI-A2L-SI-003 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-003 — Structure analysis resolution  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **EXECUTED** on feature branch. STRUCTURE WIN is **PENDING OPERATOR**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch. SI-002 rhythm was not rebuilt. Investigation A and B found no mix-first Harmonix path that avoids fabricated or separated stems. A diagnostic official mixed-audio All-In-One run invoked HTDemucs as analyzer plumbing only. That dependency is **not** accepted as an A2L product capability. Alternate structure engine (C) was not started.

Not merged. Not pushed. `deployable` / `main` not modified. Key / Mode not started.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-003-structure-resolution` |
| Base | SI-002 `feature/aci-a2l-si-002-rhythm-structure` @ `97c0cf0` |
| Implementation | recorded in ACR after commit |

## Investigation

**A. Mixed-audio path without separation:** not available. Harmonix `AllInOne` input is K=4 instrument spectrograms with cross-instrument attention. `HarmonixConfig` sets `demixed=True`, `num_instruments=4`. Official `analyze(mixed_wav)` selects HTDemucs.

**B. Config without fabricating stems:** not available. `StemsInput` requires four wavs. SI-002 mix-as-stems used the mix in all four slots and collapsed to chorus. Silence/zeros would also be fabricated.

**C. Alternate structure engine:** not started. Engine #1 structure was still diagnosable via the trained mixed path.

**Selected method:** official mixed-audio `allin1_infer.analyze()` with HTDemucs **DIAGNOSTIC**.

## Locked master

SHA-256 unchanged: `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`.  
SI-002 evidence hashes unchanged. Approved lyrics / release authority unchanged.

## Laptop evidence (observed)

| Item | Observed |
| --- | --- |
| CPU | PASS (forced `cpu`) |
| GPU required | NO |
| Cloud required | NO |
| Source separation | DIAGNOSTIC (`DemucsProvider` constructed; HTDemucs `htdemucs` 80.2 MB checkpoint) |
| Analysis wall-clock | 343.26 s (`analyze()`); run ~350 s start-to-finish |
| HTDemucs download | 80.2 MB once |
| Spectrogram | 5.84 s in-memory after separation |
| Harmonix infer | 107.64 s |
| Peak working set | 3912.2 MB |
| Cache added this run | 84,141,911 bytes (~80.2 MB HTDemucs + overhead) |
| Total isolated cache after | 95,481,209 bytes (~91.1 MB Harmonix + HTDemucs) |
| OOM / crash | none |
| Usability during run | not measured; completed without crash |

## Machine-derived structure (exact)

Do not correct labels.

```text
00:00-00:02 | start
00:02-00:21 | intro
00:21-00:40 | verse
00:40-01:00 | chorus
01:00-01:29 | verse
01:29-01:54 | chorus
01:54-02:23 | solo
02:23-02:42 | chorus
02:42-02:56 | chorus
02:56-03:14 | chorus
03:14-03:27 | outro
```

## Comparison to SI-002

SI-002 mix-as-stems was chorus-collapsed after a 2s start and one short verse. This diagnostic trained path returns intro, two verses, a solo, and an outro, with remaining consecutive chorus slices late in the song. BPM remained 98. Beat/downbeat counts shifted (321 / 80 vs SI-002 298 / 74). SI-002 remains the Rhythm WIN evidence; those counts were not rewritten.

## Authority

OUTPUT AUTHORITY: MACHINE-DERIVED  
HTDemucs as A2L product capability: NO  
SONG INTELLIGENCE RECORD: not created  
OPERATOR REVIEW REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **139 passed** (Python 3.14.3; 135 SI-002 baseline + 4 SI-003 isolation tests). Parked untracked Parakeet helpers remain ignored.

## STRUCTURE WIN

PENDING OPERATOR

---

## Minority Report

1. **HTDemucs is still not an A2L feature.** This ACI only permitted a diagnostic to test whether All-In-One's trained input restores useful structure. Adopting separation as product architecture needs a later governed decision.

2. **Late chorus repeats were not rewritten.** 02:23–03:14 is three chorus slices plus outro. Analyzer truth is preserved.

3. **Rhythm counts moved slightly** vs SI-002 because stems changed the Harmonix input. SI-002 Rhythm WIN is not reopened here.

4. **Cache-hint scanner missed the HTDemucs file name** (`955717e8-8726e21a.th`). Size was measured from the isolated cache tree (80.2 MB download observed).

5. **Quality is Operator's call.** Intro/verse/chorus/solo/outro is more differentiated than SI-002, not a CAE WIN declaration.
