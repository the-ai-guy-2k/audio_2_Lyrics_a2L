# ACI-A2L-SI-002 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-002 — Rhythm + Structure engine candidate validation  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **EXECUTED** on feature branch. ENGINE WIN is **PENDING OPERATOR**. Not merged.

---

## Execution status

COMPLETE on bounded feature branch. All-In-One / `all-in-one-infer` 3.1.0 analyzed the locked Jay master on CPU in an isolated sidecar. Mix-first path did not invoke HTDemucs. Results are MACHINE-DERIVED. No Song Intelligence Record was created. Authoritative source and governed lyric/release artifacts were not modified.

Not merged. Not pushed. `deployable` / `main` not modified. No other Song Intelligence engine was started.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-002-rhythm-structure` |
| Base | `deployable` / `main` @ `70bc6509f4c484906153efa10d8a3505ff240a3b` |
| Implementation | `d989e7f` |

## Engine

| Field | Value |
| --- | --- |
| Package | `all-in-one-infer` 3.1.0 |
| Model | `harmonix-all` (8-fold Harmonix ensemble) |
| License | MIT |
| Python | 3.12.10 sidecar `.venv-all-in-one` |
| PyTorch | 2.14.0+cpu |
| Device | cpu (forced) |
| Analysis path | mix-as-stems |
| Source separation invoked | NO |

## Locked master

| Field | Value |
| --- | --- |
| File | `01Stomp to MIX MSTR 24bit_48hz.wav` |
| SHA-256 before/after | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Ingest authoritative copy | unchanged, same SHA-256 |
| Working copy | derived 32-bit PCM for engine read only |

madmom-infer / scipy `wavfile.read(..., mmap=True)` cannot read 3-byte 24-bit samples. The spike wrote a same-rate, same-channel 32-bit PCM working copy. CONTROL A was not modified.

## Mix-first / HTDemucs

Official `allin1_infer.analyze(mixed_wav)` invokes HTDemucs, then Harmonix. `--no-demucs` and `--skip-separation` require precomputed stems.

This spike used direct stems input with the finished mix mapped to bass, drums, other, and vocals. Probes recorded:

- `separate_in_memory`: 0
- `demix`: 0
- `DemucsProvider`: 0
- HTDemucs cache files: none

`demucs-infer` is an install-time dependency. It was not invoked at runtime.

The official mixed-audio + HTDemucs workflow was **not** run and is **not** accepted as A2L design.

## Laptop evidence (observed)

| Item | Observed |
| --- | --- |
| Hardware | MSI Modern 14 B11MOU, 11th Gen Intel Core i7-1195G7, ~16 GB RAM, Intel Iris Xe |
| GPU required | NO |
| Cloud required | NO |
| Analysis wall-clock | 116.95 s (`analyze()`); run ~122 s start-to-finish |
| Spectrogram extract | 7.25 s |
| Harmonix infer | 103.91 s |
| Peak working set | 3721.7 MB |
| Model/cache added | 11,339,298 bytes (~10.8 MB) under `%USERPROFILE%\.cache\a2l-all-in-one` |
| Sidecar venv | 1,146,871,865 bytes (~1.07 GB), dominated by CPU PyTorch |
| OOM / crash | none |
| Application usability during analysis | not measured; analysis completed without crash |

## Machine-derived output

Do not treat as song facts. Do not correct because labels look wrong.

**BPM:** 98

**BEATS:** 298

**DOWNBEATS:** 74

**STRUCTURE:**

```text
00:00–00:02 start
00:02–00:19 chorus
00:19–00:36 verse
00:36–01:10 chorus
01:10–01:30 chorus
01:30–01:54 chorus
01:54–02:23 chorus
02:23–02:42 chorus
02:42–02:57 chorus
02:57–03:20 chorus
03:20–03:27 end
```

Rhythm is internally consistent with 4/4 (298 beats / 74 downbeats ≈ 4). Structure is chorus-dominated after a short start and one verse. That may be mix-as-stems degradation versus Harmonix's trained separated-stem input. Analyzer truth is preserved.

## Authority

OUTPUT AUTHORITY: MACHINE-DERIVED  
SONG INTELLIGENCE RECORD: not created  
APPROVED LYRICS / SONG RELEASE RECORD / ALBUM MANIFEST / ALBUM READINESS: unchanged  
OPERATOR REVIEW REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **135 passed** (Python 3.14.3; 129 existing + 6 SI-002 isolation tests). Parked untracked Parakeet helpers remain ignored.

## ENGINE WIN

PENDING OPERATOR

Execution completed on the Operator laptop without dedicated GPU or cloud. Licensing is MIT. Source artifacts are unchanged. Whether the chorus-heavy structure is useful enough, together with BPM/beats, is an Operator call. Perfection is not required. PARTIAL is available if rhythm is useful and structure is not.

## Explicitly not done

Key/Mode, CLAP, Lyric Intelligence, Song Intelligence Record, Song Intelligence UI, chords, source separation as an A2L feature, mastering analysis, radio/distributor logic, EPK, cloud inference, merge to deployable.

---

## Minority Report

1. **Mix-as-stems is not the trained Harmonix input.** The finished mix was presented as all four stems so HTDemucs would not run. Structure labels may be worse than the official mixed-audio + HTDemucs path. That official path was not accepted as A2L design and was not executed.

2. **Structure is almost all chorus.** That is analyzer output, not a CAE rewrite. Operator should judge usefulness against the real song, not against a corrected form.

3. **24-bit mmap failure is a real engine constraint.** A derived 32-bit working copy was required. The locked 24-bit master hash did not change.

4. **`demucs-infer` is installed but was not used.** Package size includes a separator that this spike refused to invoke. That is install overhead, not runtime separation.

5. **Peak RAM ~3.7 GB** of a 16 GB laptop. Acceptable for a spike; not proof that a future product UI stays snappy during analysis. Interactivity was not measured.

6. **Quality is not CAE's call.** BPM 98 and section timestamps are machine-derived. ENGINE WIN stays with the Operator.
