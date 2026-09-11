# ACI-A2L-015 evidence

MVP release-readiness validation. No product capability was added. Locked Jay artifacts were not rewritten. Transcription was not rerun.

- `runtime_validation.json` — startup smoke, locked-song hashes, regression counts, engine governance
- Application smoke: `python -m a2l app --host 127.0.0.1 --port 8799 --no-browser` → `GET /` 200, `GET /api/session` 200
- Supported operator URL: http://127.0.0.1:8780/

Regression: `python -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **97 passed** (Python 3.14.3).
