# Transcription draft contract (produced by ACI-ATL-002)

**Producer:** ACI-ATL-002  
**Authority:** `NON_AUTHORITATIVE_MACHINE_DRAFT`  
**Approval:** `NOT_APPROVED`

Downstream work must not infer undocumented behavior. Consume `machine_transcription/transcription_draft.json`.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-ATL-002` |
| `authority` | `NON_AUTHORITATIVE_MACHINE_DRAFT` |
| `approval_status` | `NOT_APPROVED` |
| `usable_as_approved_lyrics` | always `false` |
| `control_baseline` | `CONTROL_A` |
| `ingest_job_id` | SHA-256 job from ACI-ATL-001 |
| `input.working_audio` | `derived_working/transcription_ready.wav` |
| `input.vocal_isolation` | `not_applied` |
| `engine.technology` | baseline engine id |
| `engine.model` | model id |
| `flags` | job-level FLAG-IT codes |
| `segments` | timed engine segments with per-segment flags |
| `engine_text` | unmodified engine text |
| `draft_text` | same text; not LLM-polished |

## Rules for the next ACI

- Do not treat `engine_text` / `draft_text` as approved lyrics.
- If `NO_SIGNAL` or `ENGINE_TEXT_ON_NO_SIGNAL` is present, do not promote the text to lyrics of record.
- Do not assume vocal isolation was applied.
- Do not assume 16 kHz or mono; audio metadata is copied from the ingest manifest.
- Lyric structuring, human approval, and approved lyric artifacts are **not** produced here.
