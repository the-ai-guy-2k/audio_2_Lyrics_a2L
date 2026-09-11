# ACI-A2L-013 evidence

Derived approved-lyric export formatting. Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain authoritative.

- `a2l/export.py` — STANDARD LYRIC SHEET (default), PLAIN TEXT, STRUCTURED LYRICS
- Operator Output screen: `a2l/app.html` + `GET /api/export` + `GET /export/output.txt`
- Tests: `tests/test_export.py`, plus export assertions in `tests/test_app.py`, `tests/test_approve.py`, `tests/test_parakeet_workflow.py`

Regression: `python -m pytest tests --ignore=tests/test_parakeet_candidate.py` — 91 passed (Python 3.14.3).

Locked Jay approved TXT/JSON bytes were not rewritten by this ACI. Derived `exports/` files are written at approval time; live preview/download formats existing approved artifacts on demand.
