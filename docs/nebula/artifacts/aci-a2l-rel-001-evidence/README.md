# ACI-A2L-REL-001 evidence

Per-song release Current Truth. Not distribution.

- Branch: `feature/aci-a2l-rel-001-song-release-record`
- Base: `18852ffd4db0eae611b0c1cff9609af93090d88d`
- Implementation commit: `d5c0d7a`
- Implementation: `a2l/release_record.py`
- UI: operator app Release screen
- Tests: `tests/test_release_record.py`, `tests/test_app.py`

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **112 passed** (Python 3.14.3).
