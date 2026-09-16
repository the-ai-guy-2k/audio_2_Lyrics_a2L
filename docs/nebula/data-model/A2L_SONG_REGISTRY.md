# A2L Song Registry (ACI-A2L-DM-002)

Operational Song Registry for the Song Object Model v1.

## Purpose

Answer:

1. What Songs exist in A2L?
2. Given a `song_id`, where is that Song's governed data?

The registry assigns opaque `song_id` values and **references** existing governed artifacts. It does not replace Approved Lyrics, SIR, or Song Release Record authority.

## Persistence

```text
artifacts/song_registry/song_registry.json
```

| Field | Meaning |
| --- | --- |
| `record_type` | `A2L_SONG_REGISTRY` |
| `schema_version` | `1.0.0` |
| `songs` | map of `song_id` → stored Song shell (identity placeholders + `source.masters`) |
| `by_ingest_job_id` | idempotent index: ingest job → `song_id` |

Atomic write via tempfile + replace. Survives process restart. No database.

Module: `a2l.song_registry`

## Registration

```python
from a2l.song_registry import register_song

song = register_song("<ingest_job_id>")
```

- Allocates `song_id` as `uuid4.hex` (32 lowercase hex chars).
- `song_id` must not equal `ingest_job_id` / source SHA / filename / SIR revision.
- If the ingest job is already mapped, returns the existing Song (no duplicate).
- Does not infer title/artist from filename.
- Ambiguous unrelated ingests are never auto-merged; use `associate_master` explicitly.

## Enumeration

```python
from a2l.song_registry import list_songs

rows = list_songs()
```

Each row exposes at least:

- `song_id`
- `title` / `artist` governed value envelopes (AVAILABLE or MISSING)
- current master/source association
- approved lyrics availability/status
- Song Intelligence availability/status

## Resolution

```python
from a2l.song_registry import get_song

song = get_song(song_id)
```

Resolves a live `A2L_SONG` view:

```text
song_id
  → Identity (from song_metadata.json + ingest duration)
  → Source / masters[]
  → Lyrics refs (approved / review / draft + provenance)
  → Intelligence via SIR section refs (rhythm, key, audio, lyric)
  → Release ref
  → Relationships.albums (empty until Album Object work)
```

Intelligence properties remain in the SIR. The Song carries section references and run states, not competing copies of analyzer values.

## Multi-master

```python
from a2l.song_registry import associate_master

associate_master(song_id, other_ingest_job_id, make_current=True)
```

Same `song_id` may list Master Revision 1..N with roles `CURRENT` / `SUPERSEDED`. Full remaster UI/workflow is out of scope for DM-002.

## Identity / idempotency

| Rule | Behavior |
| --- | --- |
| Same ingest association | Same `song_id` |
| Different unrelated ingest | New Song unless explicitly associated |
| Fuzzy matching | Not performed |
| Filename as title | Forbidden |

## Existing artifact mapping

```text
artifacts/song_registry/song_registry.json
        │
        └── songs[<song_id>].source.masters[].ingest_job_id
                    ↓
artifacts/ingest/<ingest_job_id>/
  ingest_manifest.json
  authoritative_source/source.wav
  song_metadata.json
  a2l_pipeline/… approved_lyrics / review / drafts
  song_intelligence_record.json
  song_release_record.json
```

## Compatibility

DM-002 does not modify operator UI consumers, analyzers, lyric approval, SIR authority, or release behavior. Those move to registry later.

## Related

- [A2L_SONG_OBJECT_MODEL_V1.md](A2L_SONG_OBJECT_MODEL_V1.md)
- [SONG_INTELLIGENCE_RECORD.md](../../SONG_INTELLIGENCE_RECORD.md)
- [SONG_RELEASE_RECORD.md](../../SONG_RELEASE_RECORD.md)
