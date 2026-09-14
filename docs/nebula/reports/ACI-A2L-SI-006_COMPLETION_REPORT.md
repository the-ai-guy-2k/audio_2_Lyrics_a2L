# ACI-A2L-SI-006 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-006 — Lyric Intelligence engine candidate validation  
**AIW:** CAE  
**Date:** 2026-09-14  
**Recommendation:** **PASS** on feature branch. ENGINEERING WIN is **YES**. SEMANTIC VALIDATION is **PENDING JAY**. Network stop not triggered. Not merged.

---

## Execution status

COMPLETE on bounded feature branch against the APPROVED ACI. In-repo deterministic NLP analyzed the locked song's HUMAN-APPROVED lyrics (revision 2) on CPU. The WAV was not transcribed. No cloud. No model download. Network stop rule not triggered. Engine #3 / CLAP was not resumed and the incomplete CLAP transfer was not restarted. Results are MACHINE-DERIVED except lexical counts (MEASURED). The Approved Lyric Artifact was not modified. No Song Intelligence Record was created.

Not merged. Not pushed. `deployable` / `main` not modified.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-006-lyric-intelligence` |
| Base | SI-004 `feature/aci-a2l-si-004-key-mode` @ `0b0279d` |
| Implementation | `108144c` |

## Engine

| Field | Value |
| --- | --- |
| Method | stdlib tokenization, line-bounded repeated n-gram ranking, content-word frequency, bounded lexical emotion overlap |
| Packages | none added; Python 3.14 stdlib only |
| License | original A2L spike code; no third-party model weights |
| Python | 3.14.3 application interpreter |
| Device | cpu |
| Download | NO |
| Cloud | NO |

## Approved lyric input

| Field | Value |
| --- | --- |
| Path | `artifacts/ingest/<sha>/a2l_pipeline/approved_lyrics/approved_lyrics.txt` |
| JSON authority | `AUTHORITATIVE_APPROVED_LYRICS` |
| Revision | 2 |
| Source SHA-256 | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Text SHA-256 before/after | `b44a58d6e86fcf77815f9e5e17e69a0b666651b5d70b6dc61f77f93c85f1a361` |
| Draft substitution | NO |

CONTROL A audio was not read. Approved TXT/JSON hashes unchanged.

## Laptop evidence (observed)

| Item | Observed |
| --- | --- |
| GPU required | NO |
| Cloud required | NO |
| Download required | NO |
| Analysis wall-clock | 0.003 s |
| Peak working set | 23.4 MB |
| Package / model size | none (stdlib script only) |
| Sidecar venv | not created |
| OOM / crash | none |

## Machine-derived output (exact)

Do not rewrite themes because another phrasing seems more literary.

```text
THEMES:
1. hook us with that old school funk  (count=4)
2. none of that slow down ballad stuff  (count=4)
3. play something we can stomp to  (count=6)
4. these seats and move  (count=4)
5. we came here to dance and get a  (count=3)
6. came here to dance and get a little  (count=3)

KEYWORDS / CONCEPTS:
1. play  (count=9)
2. stomp  (count=8)
3. down  (count=5)
4. groove  (count=4)
5. butts  (count=4)
6. seats  (count=4)
7. move  (count=4)
8. hook  (count=4)
9. old  (count=4)
10. school  (count=4)
11. funk  (count=4)
12. slow  (count=4)

EMOTIONAL CHARACTER:
energetic

SUBJECT MATTER:
Mr. Guitar Man; hook us with that old school funk; none of that slow down ballad stuff; play something we can stomp to

SONG SYNOPSIS:
The approved lyrics open by addressing 'Mr. Guitar Man'. A repeated lyric phrase is 'hook us with that old school funk'. The same lyric body also includes: old school funk; not slow down ballad stuff; work week blues; dance and get a little footloose.

METHOD:
stdlib tokenization, line-bounded repeated n-gram ranking, content-word frequency, and bounded lexical emotion overlap on approved lyric text
```

## Authority

APPROVED LYRICS: AUTHORITATIVE INPUT  
LEXICAL COUNTS: MEASURED  
THEMES / EMOTION / SUBJECT / SYNOPSIS: MACHINE-DERIVED  
SONG INTELLIGENCE RECORD: not created  
OPERATOR / JAY REVIEW REQUIRED: YES

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py --ignore=tests/test_audio_intelligence_candidate.py` — **153 passed** (Python 3.14.3; 145 SI-004 baseline + 8 SI-006 isolation tests). Parked Parakeet helpers and deferred SI-005 CLAP tests remain ignored.

## ENGINEERING WIN

YES

SEMANTIC VALIDATION: PENDING JAY

---

## Minority Report

WHAT IS BEING DONE: Approved lyric text still contains caption-like residue (`Thanks for watching!` and `Play something we can start to`). The engine consumed the artifact unchanged and did not clean it.  
WHY IT MATTERS: Semantic outputs can include non-song residue that is present in the approved source.  
PA IMPACT: NONE for engineering; Jay semantic review may flag those lines.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Theme rank uses `count * content_tokens`, so `old school funk` outranks the more frequent `play something we can stomp to`. Engine truth is preserved; results were not rewritten.  
WHY IT MATTERS: Ranking is deterministic density, not literary importance.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Emotional character `energetic` is bounded lexicon overlap (stomp / groove / dance / funk / alive / footloose), not artist intent.  
WHY IT MATTERS: MACHINE-DERIVED emotion is not HUMAN-APPROVED meaning.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Engine #3 CLAP acquisition remains deferred. Observed incomplete `pytorch_model.bin` (~740 MB; ~139 MB / ~18%; ~245 KB/s; ~10 min; terminated). Restart not authorized. This ACI did not resume Audio Intelligence.  
WHY IT MATTERS: Distinguishes infrastructure deferral from Engine #3 technical failure and from Engine #4 success.  
PA IMPACT: NONE for this ACI  
DISPOSITION: DEFERRED (Engine #3 only)

WHAT IS BEING DONE: Semantic / musical quality is reserved for Jay. CAE accepts only that structured, grounded candidate intelligence was produced on CPU.  
WHY IT MATTERS: ENGINEERING WIN and SEMANTIC VALIDATION are separate gates.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL
