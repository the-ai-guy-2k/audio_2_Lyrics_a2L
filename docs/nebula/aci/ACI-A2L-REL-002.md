# ACI-A2L-REL-002

ALBUM RELEASE MANIFEST

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds an album-level manifest that organizes existing Song Release Records. It does not invent missing information and does not determine album release readiness.

## Constraints honored

- New branch `feature/aci-a2l-rel-002-album-release-manifest` from validated `deployable` @ `cc5dade1b3113c0433134bbe7a1e4a23e2208d0e`.
- Implementation commit: `153a116`.
- Consumes existing `artifacts/ingest/<sha256>/song_release_record.json`. Does not create competing per-song release truth.
- Operator-entered album fields only: Album Title, Primary Artist, Release Type (Album / EP / Single). Not inferred from filenames, directories, track count, or song metadata.
- Track membership references existing A2L song identity and Song Release Record.
- Track order is Operator-selected and persisted. Not inferred from WAV names, filesystem order, ingestion order, or alphabetical order.
- Removing a track from the album does not delete underlying A2L artifacts.
- Per-track READY/INCOMPLETE, approved-lyric availability, and missing fields are read live from the current Song Release Record when the album is loaded.
- Descriptive counts only (TRACKS, SONG RECORDS READY, SONG RECORDS INCOMPLETE). No ALBUM READY.
- Artifact: `artifacts/releases/<release-id>/album_release_manifest.json` using a filesystem-safe identifier, not the album title.
- Implemented in the existing operator application at http://127.0.0.1:8780/.
- `deployable` and `main` were not modified. Not merged. Not pushed. REL-003 was not started.

## Explicitly out of scope

Album Release Readiness, distributor submission, UPC/ISRC generation, copyright/PRO/publishing registration, royalty splits, artwork, marketing, mastering, unrelated song intelligence.
