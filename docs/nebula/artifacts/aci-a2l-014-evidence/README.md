# ACI-A2L-014 evidence

Optional song title and artist intake. Filename is not used as the title. Missing values are not invented.

- `a2l/metadata.py`
- Operator Upload + Review fields in `a2l/app.html`
- Tests: `tests/test_metadata.py`, plus assertions in `tests/test_app.py` and `tests/test_parakeet_workflow.py`

Regression: `python -m pytest tests --ignore=tests/test_parakeet_candidate.py` — 97 passed (Python 3.14.3).
