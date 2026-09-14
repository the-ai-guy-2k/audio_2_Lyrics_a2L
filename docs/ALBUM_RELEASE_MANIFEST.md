# Album release manifest (ACI-A2L-REL-002)

An album-level view that organizes existing A2L Song Release Records. The Operator enters album identity, chooses which ingested songs belong to the release, and sets track order.

This is **not** album-level READY, distribution, or a commercial release.

Rule: organize existing truth. Flag missing per-song information. Do not invent release data.

## Where it lives

Operator application (product-facing): http://127.0.0.1:8780/ → **Album**

Artifact:

```text
artifacts/releases/<release-id>/album_release_manifest.json
```

`<release-id>` is a filesystem-safe identifier (hex). The human-readable album title is never used as a path.

This hierarchy is separate from per-song ingest artifacts. It does not replace `song_release_record.json`.

## Album-level Operator fields

These values are Operator-entered. They are not inferred from filenames, directories, track count, or song metadata.

| Field | Values |
| --- | --- |
| Album Title | Operator text, or empty |
| Primary Artist | Operator text, or empty |
| Release Type | Album, EP, Single, or empty |

Empty stays empty. Missing is not invented.

## Track membership

Each track references an existing ingested A2L song and that song's Song Release Record.

The album file stores:

- `ingest_job_id`
- Operator-selected `position`

It does **not** store a second copy of song title, artist, duration, READY/INCOMPLETE, or missing fields as album authority.

## Track order

Operator-selected order is authoritative for this manifest.

Order is not inferred from WAV filenames, filesystem order, ingestion order, or alphabetical order.

Removing a track from the album does not delete ingest, approval, or Song Release Record artifacts.

## Current-truth behavior

When the Album screen loads (and when the manifest is assembled for the API), per-track display fields are read live from the current Song Release Record:

- Song Title
- Primary Artist
- Track Duration
- Song Release Record READY / INCOMPLETE
- Approved lyrics AVAILABLE / MISSING
- Significant missing fields (every Song Release Record field still MISSING)

If a Song Release Record changes after the album is saved, the next album load shows the updated song truth. The album file is not a frozen competing copy of those values.

To edit a missing per-song field, open that song's existing **Release** screen. Do not enter a second value on the album.

## Album-level status

Descriptive counts only:

- TRACKS
- SONG RECORDS READY
- SONG RECORDS INCOMPLETE

This capability does **not** determine DISTRIBUTION READY, RELEASE READY, PUBLISHING READY, or RELEASED. A2L internal album completeness is assessed separately by [ALBUM_RELEASE_READINESS.md](ALBUM_RELEASE_READINESS.md).

## Provenance

Album title, primary artist, and release type are `OPERATOR_ENTERED`. Track order is `OPERATOR_SELECTED`.

## Out of scope

Distributor submission, UPC/ISRC generation, registrations, royalty splits, artwork, marketing, mastering. Release Package Export belongs to a later ACI.
