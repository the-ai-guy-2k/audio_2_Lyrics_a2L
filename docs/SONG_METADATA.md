# Song metadata intake (ACI-A2L-014)

Optional identifying fields so a finished lyric sheet can show a song title and artist without inventing them.

## Fields

| Field | Required | Source |
| --- | --- | --- |
| Song title | No | Operator entry |
| Artist | No | Operator entry |

The WAV filename is never treated as the title.

## Flow

```text
UPLOAD (optional title + artist shown with the selected song)
  → SONG METADATA (ingest_job/song_metadata.json)
  → TRANSCRIPTION / REVIEW / APPROVAL
  → approved_lyrics.json (song_title / artist if supplied)
  → STANDARD LYRIC SHEET header when values exist
```

Metadata is independent from machine lyric lines. Empty fields stay empty.

## Editing

Before approval, title and artist can be corrected on Review and saved with the draft.

After approval they are not silently changed. Reopen, correct, save, and reapprove to include new values in the next authoritative revision.

## Output

If title and artist exist:

```text
Song Title
Artist

approved lyric body...
```

If only one exists, that one is shown. If neither exists, the lyric body is shown with no invented header.

PLAIN TEXT remains the canonical lyric body. STRUCTURED LYRICS remains section presentation only.

## Download filenames

User-downloaded lyric files use the same operator-supplied fields (ACI-A2L-016). Example when both exist: `Jay Garrett - Stomp To.txt`. Title-only, artist-only, and missing-metadata fallbacks are documented in [APPROVED_EXPORT.md](APPROVED_EXPORT.md). Filename sanitization does not change stored `song_title` / `artist`.

