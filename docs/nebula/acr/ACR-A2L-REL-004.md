# ACR-A2L-REL-004 — ACI-A2L-REL-004 acceptance

**ACI:** ACI-A2L-REL-004 — Release package export  
**Date recorded:** 2026-09-14  
**Branch:** `feature/aci-a2l-rel-004-release-package-export`  
**Commit:** `5e0593c`  
**Status:** COMPLETE on feature branch — not merged  
**Product changes:** portable A2L release-preparation ZIP from current Album Release Manifest, Album Release Readiness, Song Release Records, and approved lyric exports; derived only; not distribution.

## Accepted outcome

READY and INCOMPLETE albums can export a ZIP. INCOMPLETE packages preserve A2L INTERNAL RELEASE READINESS and blocking gaps. The package includes a machine-readable manifest, human-readable summary, album authority copies, current song records in album order, approved lyric exports when available, and provenance back to governed sources. Master WAV is not copied. Missing metadata is not invented. ISRC/UPC are not generated. Distributor packages are not implemented.

RELEASE PACKAGE EXPORT: AVAILABLE  
OPERATOR UI: AVAILABLE  
ZIP EXPORT: PASS  
READY PACKAGE: PASS  
INCOMPLETE PACKAGE: PASS  
PACKAGE MANIFEST: PASS  
RELEASE SUMMARY: PASS  
ALBUM MANIFEST INCLUDED: YES  
READINESS ASSESSMENT INCLUDED: YES  
SONG RELEASE RECORDS INCLUDED: PASS  
APPROVED LYRIC EXPORTS INCLUDED: PASS  
PROVENANCE: PASS  
CURRENT TRUTH: PASS  
MASTER AUDIO AUTOMATICALLY INCLUDED: NO  
DISTRIBUTOR PACKAGE IMPLEMENTED: NO  
RELEASE DATA INVENTED: NO  
APPROVED LYRIC AUTHORITY MODIFIED: NO  
ACI-A2L-REL-004: PASS

## Evidence (in repo)

- `a2l/release_package.py`
- `a2l/app.html` Album → Export release package
- `tests/test_release_package.py`
- `docs/RELEASE_PACKAGE_EXPORT.md`
- `docs/nebula/reports/ACI-A2L-REL-004_COMPLETION_REPORT.md`

## Gaps

- Distributor-specific packages, distribution audio, ISRC/UPC generation, and API submission remain later capabilities.
- Engineering review page does not include package export. Operator-app Album is the governed path.
- Direct ZIP download regenerates from current truth; a POST to `/api/release-package` followed by GET `/export/release-package` writes two derived export folders.
