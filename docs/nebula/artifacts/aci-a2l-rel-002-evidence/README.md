# ACI-A2L-REL-002 evidence

Album Release Manifest. Organizes existing Song Release Records. Not album READY. Not distribution.

- Branch: `feature/aci-a2l-rel-002-album-release-manifest`
- Base: `cc5dade1b3113c0433134bbe7a1e4a23e2208d0e`
- Implementation commit: `153a116`
- Implementation: `a2l/album_manifest.py`
- UI: operator app Album screen
- Tests: `tests/test_album_manifest.py`, `tests/test_app.py`

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **118 passed** (Python 3.14.3).
