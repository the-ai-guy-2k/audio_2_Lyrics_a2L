# ACI-A2L-017 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-017 — MVP baseline promotion to deployable  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** recorded after promotion

---

## Execution status

Documentation cleanup, 011/012 traceability restoration from existing evidence, regression, and promotion to `deployable`. No product capability added.

## Source baseline

| Item | Value |
| --- | --- |
| Source branch | `feature/aci-a2l-016-export-filenames` |
| Validated implementation | `3937749547503d4ad5264771db3cd09496b2ad94` |
| Extract-button repair | present (`displayText` in `a2l/app.html`) |

## Pre-merge hygiene

Working tree on source: parked untracked items only. None committed. None deleted.

- `a2l.egg-info/`
- `docs/nebula/artifacts/aci-a2l-005-evidence/`
- `requirements-parakeet.txt`
- `scripts/run_parakeet_candidate.py`
- `tests/test_parakeet_candidate.py`

No secrets staged. Canonical `approved_lyrics.txt` / `.json` not rewritten.

## Main-branch assessment (Current Truth)

- No local `refs/heads/main`.
- No `refs/remotes/origin/*` after `git fetch`.
- `git ls-remote origin` returned no heads (empty remote from this workstation).
- Leftover config only: `branch.main.remote=origin` and `branch.main.merge=refs/heads/main` without a branch.
- `gh` is not logged in (`gh auth status` failed). Git fetch/ls-remote exited 0 with empty refs.

There are **no unique `main` commits** to destroy. Creating `main` at the `deployable` tip is first-time baseline creation, not a force over divergent history.

## Documentation cleanup

Root README now leads with the operator application, primary `.venv-faster-whisper` start, PRIMARY vs ALTERNATE engines, and :8780 vs :8765. OPERATOR_START.md and FRONTEND.md match. Default Python 3.14 is documented as UI-capable only, not faster-whisper extract.

## Traceability

- ACR-A2L-011 written from existing 011 evidence (candidate run; not promoted; no invented quality verdict).
- ACR-A2L-012 written from existing 012 completion report and evidence (alternate engine; not promoted; Parakeet lyrics not approved).
- No ACI-A2L-011 completion report exists in-tree; that gap is recorded in ACR-A2L-011.

## Regression / promotion / push

Filled after the suite run and branch operations.
