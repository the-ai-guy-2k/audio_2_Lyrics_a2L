# ACI-A2L-017 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-017 — MVP baseline promotion to deployable  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (promoted to `deployable`; not deployed to cloud)

---

## Execution status

COMPLETE. Documentation cleanup, 011/012 traceability restoration from existing evidence, regression (104 passed), and promotion to `deployable`. No product capability added.

## Branch / commits

| Item | Value |
| --- | --- |
| Source branch | `feature/aci-a2l-016-export-filenames` |
| Source commit | `3937749547503d4ad5264771db3cd09496b2ad94` |
| 017 branch | `feature/aci-a2l-017-mvp-baseline-promotion` |
| Implementation | `a197bf5` |
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

## Regression

| Item | Value |
| --- | --- |
| Python | 3.14.3 |
| Command | `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` |
| Result | **104 passed**, 0 failed |
| Ignored | untracked parked `tests/test_parakeet_candidate.py` |

## Promotion / push

| Item | Value |
| --- | --- |
| Merge strategy | `git checkout -b deployable 3937749` then `git merge --no-ff feature/aci-a2l-017-mvp-baseline-promotion` |
| `deployable` | `57bebf1bfec1794e697c2a135b434ee5ce5e0c24` |
| `main` | created at the same commit (no prior `main` history) |
| Cloud deploy | not performed |

Remote push results are recorded after `git push`.
