# ACI-A2L-REL-004

RELEASE PACKAGE EXPORT

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds a portable A2L release-preparation ZIP from current governed album truth. It does not invent missing information and does not claim distributor or commercial release.

## Constraints honored

- New branch `feature/aci-a2l-rel-004-release-package-export` from validated `deployable` @ `2a754ed07a6e7513a4f3a6e1376696f67a04b6ec`.
- Implementation commit recorded in ACR-A2L-REL-004.
- Consumes existing Album Release Manifest, Album Release Readiness, Song Release Records, and approved lyric exports. Does not create competing authority.
- READY and INCOMPLETE albums may both export. INCOMPLETE status and blocking gaps are preserved in the package.
- ZIP is a derived artifact under `artifacts/releases/<release-id>/exports/`.
- Master WAV files are referenced, not copied.
- Implemented in the existing operator application at http://127.0.0.1:8780/.
- `deployable` and `main` were not modified. Not merged. Not pushed. Phase 2 was not started.

## Explicitly out of scope

Distributor/store packages (Spotify, Apple Music, DistroKid, TuneCore, CD Baby), audio transcoding, 44.1/16 WAV or MP3 generation, loudness correction, mastering, Audio Asset Inspector, Distribution Audio Generator, Distribution Metadata Export, ISRC/UPC generation, external distribution, API submission, radio readiness, EPK, marketing, copyright/publishing/PRO registration.
