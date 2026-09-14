# ACI-A2L-REL-004 evidence

A2L release-preparation ZIP export. Derived package, not distributor acceptance.

- Branch: `feature/aci-a2l-rel-004-release-package-export`
- Base: `2a754ed07a6e7513a4f3a6e1376696f67a04b6ec`
- Implementation commit: `5e0593c`
- Implementation: `a2l/release_package.py`
- UI: operator app Album → Export release package
- Tests: `tests/test_release_package.py`, `tests/test_app.py`

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **129 passed** (Python 3.14.3).
