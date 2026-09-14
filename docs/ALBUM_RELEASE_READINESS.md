# Album release readiness (ACI-A2L-REL-003)

Deterministic **A2L INTERNAL RELEASE READINESS** for an album. The assessment consumes the existing Album Release Manifest and current Song Release Records. Missing information is flagged. Values are not invented.

READY means the album satisfies A2L's release-information completeness rules at this stage.

READY does **not** mean commercially released, distributor accepted, store-ready, legally registered, or delivered to any external service.

## Where it lives

Operator application (product-facing): http://127.0.0.1:8780/ → **Album** → Release Readiness

Artifact:

```text
artifacts/releases/<release-id>/album_release_readiness.json
```

This sits next to `album_release_manifest.json`. It does not replace the manifest or `song_release_record.json`.

## Rules

Album INTERNAL READY requires all of:

1. Album Title, Primary Artist, and Release Type are present.
2. The album contains at least one track.
3. Every track resolves to an existing ingested A2L song.
4. Every track's current Song Release Record satisfies ACI-A2L-REL-001 READY rules.
5. Required approved lyrics are available for every included song.

If any required condition fails, overall state is **INCOMPLETE**.

Per-song required fields are unchanged from REL-001: Song Title, Primary Artist, Track Duration, Explicit / Clean, Songwriter(s), Copyright Year, Copyright Owner, Approved Lyrics.

Optional missing fields (including ISRC) are reported as **MISSING — OPTIONAL** and do not block INTERNAL READY.

## Current-truth behavior

Each assessment/load recalculates from the current manifest and current Song Release Records. The readiness file is an assessment record, not a competing copy of per-song metadata. After a Song Release Record is corrected, Assess / reload uses the updated song truth.

Track membership and order remain owned by the Album Release Manifest.

## Out of scope

Distributor/store readiness, ISRC/UPC generation, registrations, Release Package Export, marketing, mastering.
