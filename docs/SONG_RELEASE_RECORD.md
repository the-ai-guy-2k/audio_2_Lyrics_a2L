# Song release record (ACI-A2L-REL-001)

A per-song record of release Current Truth. It prepares one ingested song for an album or release. It does **not** distribute, deliver to a distributor, register copyright or publishing, or commercially release the song.

Rule: use known truth. Flag missing information. Do not invent release data.

## Where it lives

Operator application (product-facing): http://127.0.0.1:8780/ → **Release**

Artifact:

```text
artifacts/ingest/<sha256>/song_release_record.json
```

This sits next to `song_metadata.json` and `ingest_manifest.json`. It does not replace approved lyrics.

## Existing A2L truth reused

| Field | Source |
| --- | --- |
| Song Title | Operator-entered `song_metadata.json` / review (WAV filename is never the title) |
| Primary Artist | Same artist metadata |
| Track Duration | Ingest audio metadata (`duration_seconds`) |
| Master Audio | Authoritative ingested `authoritative_source/source.wav` |
| Approved Lyrics | Reference to `approved_lyrics.txt` / `.json` when APPROVED |

Title and artist stay on the existing metadata authority. Editing them on the Release screen updates that same metadata. After lyrics are APPROVED, title/artist cannot change until reopen.

Approved lyric **words** are not copied into the release record.

## Operator-entered fields

Featured artist(s), track number, disc number, explicit/clean, songwriter(s), composer(s), producer(s), copyright year, copyright owner, publisher, ISRC.

ISRC is stored if the operator enters it. A2L never generates an ISRC.

## Field status

Each field is **AVAILABLE** or **MISSING**. Missing is not an application error.

## Readiness

Internal status only: **READY** or **INCOMPLETE**.

READY requires:

- Song Title
- Primary Artist
- Track Duration
- Explicit / Clean status
- Songwriter(s)
- Copyright Year
- Copyright Owner
- Approved Lyrics

Optional (do not block READY): Featured Artist(s), Track Number, Disc Number, Composer(s), Producer(s), Publisher / Publishing Information, ISRC.

Track Number is optional at the individual-song stage. Album sequencing is out of scope.

## Out of scope

Album-wide management, UPC/ISRC generation, distributor submission, streaming-store integrations, copyright/PRO/publishing registration, royalty splits, artwork, marketing, scheduling.
