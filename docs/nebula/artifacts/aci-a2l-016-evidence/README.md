# ACI-A2L-016 evidence

User-downloaded lyric filenames from operator-supplied Artist and Song Title. Canonical approved artifacts are not renamed. Lyric content is not changed.

- Branch: `feature/aci-a2l-016-export-filenames`
- Base: `f9532c95dfd77c6cb7f4023a3d1d7623999a5dc5`
- Implementation: `a2l/export.py` (`export_download_name`, `sanitize_filename_component`)
- Download header: `a2l/app_server.py` `content_disposition_attachment`
- Output link: `a2l/app.html` `download` attribute from `payload.download_name`
- Tests: `tests/test_export.py` filename cases; `tests/test_app.py` Content-Disposition

Regression: `py -3.14 -m pytest tests --ignore=tests/test_parakeet_candidate.py` — **104 passed** (Python 3.14.3).
