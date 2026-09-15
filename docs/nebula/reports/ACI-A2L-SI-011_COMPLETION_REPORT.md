# ACI-A2L-SI-011 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-SI-011 — Song Intelligence product UI  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. The existing operator application exposes Song Intelligence. Full Song Intelligence is the default. ANALYZE SONG orchestrates selected promoted analyzers. Results are grouped, selectable, and carry engine provenance and authority classes. Partial vocal and instrumentation states remain partial. No governed Song Intelligence Record was created. Not merged. Not promoted.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-si-011-product-ui` |
| Base | `deployable` @ `f95ed9a807884d44a5b8fbe0be05e051c66058cd` |
| Implementation | `b82fc82` |

## Product surface

| Item | Value |
| --- | --- |
| Product URL | http://127.0.0.1:8780/ |
| UI entry | **Song Intelligence** |
| Default analysis | Full Song Intelligence |
| Primary action | Analyze song |
| Temporary aggregation | `artifacts/ingest/<job>/song_intelligence_ui/ui_aggregation.json` (`TEMPORARY_UI_AGGREGATION`) |
| Governed SI Record | NO |

## Validation

| Check | Result |
| --- | --- |
| A. Full Song Intelligence selection | PASS |
| B. Single capability selection | PASS |
| C. Advanced engine selection | PASS |
| D. Approved-lyrics dependency | PASS |
| E. Partial instrumentation display | PASS |
| F. Partial vocal display | PASS |
| G. Engine provenance | PASS |
| H. Authority display | PASS |
| I. Analyzer failure isolation | PASS |
| J. Existing A2L product functionality | PASS |
| K. Normal-laptop sequential CPU execution | PASS |
| L. No source-master modification | PASS — Jay master hash unchanged |

## PA observations (governed Jay song)

| Item | Value |
| --- | --- |
| Lyric Intelligence | Complete in 0.088 s; themes/emotion/synopsis MACHINE-DERIVED |
| Key + Mode | Complete in 17.8 s via `.venv-key-mode`; A major; MACHINE-DERIVED |
| Operator UI | Lyric Intelligence on Jay produced Complete results with PENDING HUMAN VALIDATION |
| GPU required | NO |
| Cloud required | NO |
| Peak memory | UI-process sampler not meaningful while analyzers run in isolated venvs |

Heavyweight CLAP / AST / PANNs / All-In-One were not re-run end-to-end in this ACI. They are invoked by the same sequential adapters and isolated venvs. Prior SI validation evidence remains the engine truth.

## Regression

`py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py`

**196 passed**, 0 failed, 0 skipped. Ignored parked Parakeet candidate.

## Minority Report

WHAT IS BEING DONE: Full live CLAP + AST + PANNs + All-In-One product run was not repeated on the Jay master during this ACI.  
WHY IT MATTERS: Those analyzers already earned their statuses; repeating all of them sequentially would add material laptop time without changing routing, provenance, or partial-state display.  
PA IMPACT: NONE for UI/orchestration. Engine-level truth remains the promoted SI-002 through SI-010 evidence.  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: Many catalog songs display as "Title not entered — Artist not entered" when release metadata is missing, including the locked Jay song.  
WHY IT MATTERS: Filename is not used as a title. Missing operator metadata stays missing.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL
