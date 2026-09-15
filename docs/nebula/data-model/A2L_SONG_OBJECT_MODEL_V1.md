# A2L Song Object Model v1

**ACI:** ACI-A2L-DM-001  
**Status:** DEFINED (documentation capability; not implemented as a registry)  
**Baseline:** `deployable` @ `d5e3c85ed128a8fdc124adaa2dee7c150d3da311`  
**Record type (future instance):** `A2L_SONG`  
**Schema version:** `1.0.0`

## Purpose

Define the canonical governed **Song** domain object for A2L.

A2L today is ingest/artifact-centric: one master WAV SHA-256 creates one ingest job directory, and lyrics, Song Intelligence, and release truth hang from that directory. The Song Object sits **above** those artifacts as the product-domain representation of a musical work, without replacing their authority.

This document is the required capability for ACI-A2L-DM-001. It does **not** implement a Song Registry, migrate storage, change the UI, or alter analyzer/lyric/release behavior.

## Governing rules

1. Existing governed artifacts remain authoritative according to their existing rules.
2. The Song Object resolves and owns **references** to those artifacts; it does not become a competing copy of their facts.
3. Machine-derived intelligence remains MACHINE-DERIVED when exposed through Song.
4. Missing stays missing. Filename is never title. Folder structure is never artist. Album membership is never inferred.
5. `song_id` is not ingest job identity, not source SHA-256, not filename, not SIR revision, and not an analyzer run id.

## Object overview

```text
SONG (A2L_SONG)
│
├── Identity
│   ├── song_id
│   ├── title
│   ├── artist
│   └── duration
│
├── Source / masters
│   ├── current master reference
│   ├── source SHA-256
│   └── master revision history (same Song, N masters)
│
├── Lyrics          → reference Approved Lyrics (+ transcription provenance)
├── Rhythm & Structure → reference SIR.rhythm_structure
├── Key & Mode         → reference SIR.key_mode
├── Audio Intelligence → reference SIR.audio_intelligence
├── Lyric Intelligence → reference SIR.lyric_intelligence
├── Release            → reference Song Release Record
└── Relationships      → Album membership references (no Album authority copy)
```

## Identity rules

### song_id

| Rule | Requirement |
| --- | --- |
| Stability | Opaque product identity for one Song across master revisions |
| Format (v1) | 32-character lowercase hex (`uuid4.hex`) when a future registry assigns one |
| Forbidden equals | `ingest_job_id`, source SHA-256, WAV filename, SIR `revision`, analyzer execution id, album `release_id` |
| Assignment | Deferred to a future Song Registry ACI. This model defines the field; it does not allocate ids. |

### Separation from current artifact keys

Today A2L stores songs under:

```text
artifacts/ingest/<ingest_job_id>/
```

where `<ingest_job_id>` is the SHA-256 of the ingested master WAV (`a2l.ingest.ingest_wav`). That equality is an **implementation coincidence of the ingest store**, not Song identity.

| Identifier | What it identifies |
| --- | --- |
| `song_id` | The musical Song (domain object) |
| `ingest_job_id` | One governed ingest artifact tree for one master bytes object |
| source SHA-256 | One immutable master audio asset |
| SIR `revision` | One generation of Song Intelligence Record current truth |
| album `release_id` | One Album Release Manifest |

### Same Song, multiple masters

```text
Same Song (song_id)
    ├── Master revision 1  → source_sha256_A / ingest_job_id_A
    ├── Master revision 2  → source_sha256_B / ingest_job_id_B
    └── Master revision N  → source_sha256_N / ingest_job_id_N
```

A new master does **not** require a new Song. A future registry associates the new ingest job as another `masters[]` entry and marks which revision is `CURRENT`. This ACI defines that relationship only; it does not implement master-replacement workflow.

## Field / schema definition

Conceptual JSON shape. Intelligence and release blocks prefer **references** to governed artifacts over duplicated values.

```json
{
  "record_type": "A2L_SONG",
  "schema_version": "1.0.0",
  "song_id": "<opaque-hex-uuid>",
  "identity": {
    "title": { "value": null, "status": "MISSING", "authority": "AUTHORITATIVE INPUT", "source_ref": null },
    "artist": { "value": null, "status": "MISSING", "authority": "AUTHORITATIVE INPUT", "source_ref": null },
    "duration_seconds": { "value": null, "status": "MISSING", "authority": "MEASURED", "source_ref": null }
  },
  "source": {
    "current_master_revision": null,
    "masters": [
      {
        "master_revision": 1,
        "role": "CURRENT",
        "source_sha256": "<sha256>",
        "ingest_job_id": "<ingest_job_id>",
        "source_ref": "ingest/<ingest_job_id>/authoritative_source/source.wav",
        "working_ref": "ingest/<ingest_job_id>/derived_working/transcription_ready.wav",
        "ingest_manifest_ref": "ingest/<ingest_job_id>/ingest_manifest.json",
        "associated_at": null,
        "notes": "Master bytes identify an audio asset, not the Song."
      }
    ]
  },
  "lyrics": {
    "approved_lyrics_ref": null,
    "review_ref": null,
    "transcription_draft_ref": null,
    "pipeline_dirname": null,
    "approval_status": "NOT_APPROVED",
    "lyric_revision": null,
    "authority": null,
    "transcription_provenance": {
      "engine": null,
      "model": null,
      "generated_at": null
    }
  },
  "intelligence": {
    "sir_ref": null,
    "sir_revision": null,
    "rhythm_structure": { "section_ref": "sir.rhythm_structure", "run_state": "NOT_RUN" },
    "key_mode": { "section_ref": "sir.key_mode", "run_state": "NOT_RUN" },
    "audio_intelligence": { "section_ref": "sir.audio_intelligence", "run_state": "NOT_RUN" },
    "lyric_intelligence": { "section_ref": "sir.lyric_intelligence", "run_state": "NOT_RUN" }
  },
  "release": {
    "song_release_record_ref": null,
    "release_readiness": null
  },
  "relationships": {
    "albums": [
      {
        "release_id": null,
        "album_manifest_ref": null,
        "position": null
      }
    ]
  },
  "lifecycle_state": "UNREGISTERED",
  "notes": []
}
```

Machine-readable companion: [a2l_song_object_model_v1.schema.json](a2l_song_object_model_v1.schema.json).

### Property envelope (authority / provenance)

Song-facing intelligence properties resolve through the SIR property envelope. Example conceptual resolution:

```text
Song.rhythm.bpm
  value:       <from SIR.rhythm_structure fields>
  authority:   MACHINE-DERIVED
  source_engine / analyzer_id: rhythm_structure
  validation:  existing SIR human_validation / engineering status
  run_state:   AVAILABLE | PARTIAL | UNAVAILABLE | FAILED | NOT_RUN
  sir_revision:<n>
  result_origin: GENERATED | REUSED | NOT_RUN
```

The Song Object MUST NOT rewrite `authority` to HUMAN-APPROVED merely by projection.

### Identity property sources

| Song field | Governed source today | Authority |
| --- | --- | --- |
| title | `song_metadata.json` / review / approved lyrics metadata | AUTHORITATIVE INPUT (operator); never filename |
| artist | same | AUTHORITATIVE INPUT |
| duration_seconds | `ingest_manifest.json` → `audio.duration_seconds` | MEASURED |

## Intelligence domains

These map 1:1 to SIR top-level sections (`a2l/song_intelligence_record.py`):

| Song area | SIR section | Typical authority |
| --- | --- | --- |
| Lyrics (approved) | `lyrics` | HUMAN-APPROVED / AUTHORITATIVE for approved lyric text |
| Rhythm & Structure | `rhythm_structure` | MACHINE-DERIVED (BPM, beats, downbeats, sections, boundaries) |
| Key & Mode | `key_mode` | MACHINE-DERIVED (key, mode, confidence/evidence, alternates when present) |
| Audio Intelligence | `audio_intelligence` | MACHINE-DERIVED categories: energy/intensity, acoustic/electronic, genre/style, vocal, instrumentation |
| Lyric Intelligence | `lyric_intelligence` | MEASURED lexical counts; MACHINE-DERIVED themes/keywords/subject/emotion/synopsis |

PARTIAL, UNAVAILABLE, FAILED, and NOT RUN remain first-class. Temporary UI aggregation at `song_intelligence_ui/ui_aggregation.json` is **not** a Song authority source (`outranks_sir: false`).

## Release and album relationships

| Relationship | Artifact | Song Object behavior |
| --- | --- | --- |
| Song release truth | `artifacts/ingest/<ingest_job_id>/song_release_record.json` | Reference only; READY/INCOMPLETE and field MISSING stay on that record |
| Album membership | `artifacts/releases/<release_id>/album_release_manifest.json` | Store `release_id` + position reference; do not copy album title/artist/readiness as Song authority |
| Approved lyrics | `a2l_pipeline/approved_lyrics/approved_lyrics.{txt,json}` (or Parakeet pipeline dirname when that chain is active) | Reference; lyric words are not duplicated into Song or release records |

Album organizes Songs. Song does not own Album authority.

## Lifecycle (conceptual)

```text
Song created/registered          (future Song Registry; lifecycle_state=REGISTERED)
        ↓
Master associated                (masters[] entry; CURRENT master set)
        ↓
Lyrics produced/reviewed/approved
        ↓
Song Intelligence generated/revised  (SIR revision N; Song.intelligence.sir_revision tracks current)
        ↓
Release information populated    (Song Release Record)
        ↓
Album relationship established   (Album manifest track membership)
```

### Existing Song + new master

```text
Song (same song_id)
  masters[n] role=SUPERSEDED
  masters[n+1] role=CURRENT  ← new source_sha256 / ingest_job_id
```

Downstream lyrics/SIR/release for the new master are new or re-derived artifact trees under the new ingest job. Prior master artifacts remain intact. No automatic merge of approved lyrics across masters is implied by this model.

Until a registry exists, product lifecycle remains the current ingest-job workflow. `lifecycle_state=UNREGISTERED` means the Song Object is a mapping view over an existing ingest job, not a persisted registry row.

## Existing artifact mapping

```text
Master WAV (operator file; never modified)
        ↓ ingest (ACI-ATL-001)
artifacts/ingest/<ingest_job_id>/
  ingest_manifest.json
  authoritative_source/source.wav
  derived_working/transcription_ready.wav
  song_metadata.json
  a2l_pipeline/… or a2l_pipeline_parakeet/…
    machine_transcription/
    uncertainty/
    structured_lyrics/
    human_review/
    approved_lyrics/          ← Approved Lyrics authority
  song_intelligence_record.json (+ history/)  ← SIR authority
  song_release_record.json                    ← Release authority
        ↓
Song Object (domain resolution layer; references above)
        └── relationships.albums[] → artifacts/releases/<release_id>/album_release_manifest.json
```

### Concrete mapping example (locked Jay master)

Evidence inspected on workstation under the governed ingest job (not modified by this ACI):

| Model slot | Actual repository value / path |
| --- | --- |
| Provisional Song (unregistered) | Mapped from ingest job only; **no `song_id` allocated** by this ACI |
| ingest_job_id / source SHA-256 | `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` |
| Master filename (operator) | `01Stomp to MIX MSTR 24bit_48hz.wav` (not title) |
| title | `Stomp to` from `song_metadata.json` (AUTHORITATIVE INPUT) |
| artist | `Jay Garrett` from `song_metadata.json` (AUTHORITATIVE INPUT) |
| duration | `207.12120833333333` from ingest manifest (MEASURED) |
| Approved lyrics | `a2l_pipeline/approved_lyrics/approved_lyrics.json` — `APPROVED` / `AUTHORITATIVE_APPROVED_LYRICS`; transcription provenance `faster-whisper` / `large-v3` |
| SIR | `song_intelligence_record.json` revision `1` |
| Rhythm & Structure | SIR `rhythm_structure.run_state` = `UNAVAILABLE` (preserved; not invented) |
| Key & Mode | SIR `key_mode` AVAILABLE — key `A`, mode `major`, authority MACHINE-DERIVED, human validation pending |
| Audio Intelligence | SIR `audio_intelligence.run_state` = `PARTIAL` (genre AVAILABLE; instrumentation PARTIAL; several categories FAILED/unavailable on this record) |
| Lyric Intelligence | SIR `lyric_intelligence` AVAILABLE with themes/keywords/synopsis MACHINE-DERIVED; token/line counts MEASURED |
| Release | `song_release_record.json` — `release_readiness: INCOMPLETE`; missing required: Explicit/Clean, Songwriter(s), Copyright Year, Copyright Owner |
| Album relationship | No album membership required for Song validity; if present, album stores `ingest_job_id` + position only |

This example proves the model can represent master + approved lyrics + SIR + partial intelligence + missing release fields without migrating artifacts.

## Missing-data behavior

| Situation | Song Object behavior |
| --- | --- |
| No operator title/artist | `status: MISSING`; do not use filename or folder |
| No approved lyrics | `lyrics.approval_status` remains not approved; refs null or draft-only |
| SIR section not run | `run_state: NOT_RUN` |
| Analyzer unavailable/failed/partial | Preserve SIR run_state; do not invent BPM/key/genre |
| No Song Release Record | `release` refs null; readiness null |
| No Album membership | `relationships.albums` empty |

## Compatibility considerations

| Allowed now | Forbidden by this ACI |
| --- | --- |
| Continue product on `ingest_job_id` paths | Migrate or rewrite ingest storage |
| Document Song above artifacts | Implement Song Registry |
| Reference SIR/lyrics/release | Duplicate authoritative lyric/SI/release facts into a competing store |
| Future master-revision association | Implement master-replacement UI/workflow |
| Keep :8780 operator app unchanged | Change UI, ports, analyzers, lyric authority, SIR authority, release behavior |

No database is required by v1 of the model. A future registry may persist `A2L_SONG` instances; that persistence is out of scope here.

## Related documentation

- [SONG_METADATA.md](../../SONG_METADATA.md)
- [SONG_INTELLIGENCE_RECORD.md](../../SONG_INTELLIGENCE_RECORD.md)
- [SONG_RELEASE_RECORD.md](../../SONG_RELEASE_RECORD.md)
- [ALBUM_RELEASE_MANIFEST.md](../../ALBUM_RELEASE_MANIFEST.md)
- [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)
- [current-architecture.md](../architecture/current-architecture.md)
