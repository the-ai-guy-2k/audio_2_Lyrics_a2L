# Release package export (ACI-A2L-REL-004)

A portable **A2L RELEASE PREPARATION PACKAGE** built from current governed album truth. The ZIP collects existing album, song, readiness, and approved-lyric artifacts. Missing information is preserved. Values are not invented.

The package is for operator review, release preparation, later distribution handoff, and archive. It is **not** proof of distributor acceptance or commercial release.

## Where it lives

Operator application (product-facing): http://127.0.0.1:8780/ → **Album** → **Export release package**

Derived output:

```text
artifacts/releases/<release-id>/exports/<generation-stamp>/<safe-name>_A2L_Release_Package.zip
```

The ZIP is a derived export. It does not replace:

- `album_release_manifest.json`
- `album_release_readiness.json`
- `song_release_record.json`
- canonical approved lyrics

## Eligibility

READY and INCOMPLETE albums can both export. INCOMPLETE does not block export. The package keeps:

```text
A2L INTERNAL RELEASE READINESS:
READY
```

or

```text
A2L INTERNAL RELEASE READINESS:
INCOMPLETE
```

and lists blocking gaps when INCOMPLETE.

## Filename

When album title and primary artist are known:

`Jay_Garrett_<Album_Title>_A2L_Release_Package.zip`

Unsafe filename characters are sanitized. If governed identity is missing, the filename uses the release identity. Title and artist are not invented to name the file.

## Package contents

- `package_manifest.json` — derived package manifest
- `release_summary.txt` — factual human-readable summary
- `album/album_release_manifest.json` — copy of governed album authority
- `album/album_release_readiness.json` — current internal readiness (reassessed at export)
- `tracks/<nn>_<safe-track-name>/song_release_record.json` — current song records in album order
- `tracks/.../lyrics/` — existing approved lyric exports when available
- `provenance/source_references.json` — governed source references, including source audio SHA-256 when already known

Master WAV files are referenced, not copied.

## Current truth

Each export reassesses album readiness and reads current Song Release Records and approved-lyric state. A later export after a song-record correction writes a new derived ZIP. Prior export folders are left in place.

## Out of scope

Distributor/store packages, audio transcoding, 44.1/16 WAV or MP3 generation, loudness/mastering, ISRC/UPC generation, API submission, radio, EPK, marketing, registrations.
