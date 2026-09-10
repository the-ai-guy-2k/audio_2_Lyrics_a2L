# Uncertainty report contract (produced by ACI-ATL-003)

**Producer:** ACI-ATL-003  
**Input:** ACI-ATL-002 `transcription_draft.json`

Downstream work must not treat this report as approved lyrics.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-ATL-003` |
| `authority_boundary.mastered_audio` | `AUTHORITATIVE_SOURCE` |
| `authority_boundary.machine_transcription` | `NON_AUTHORITATIVE_DRAFT` |
| `authority_boundary.uncertainty_flag` | `REQUIRES_LATER_RESOLUTION` |
| `usable_as_approved_lyrics` | always `false` |
| `established_lyrics_present` | always `false` in this ACI |
| `preserved_engine_text` | unmodified engine text |
| `rewritten_text` | always `null` |
| `llm_interpretation` | always `false` |
| `job_status` | `REQUIRES_LATER_RESOLUTION` or `UNVERIFIED_MACHINE_TEXT` |
| `items[].status` | per-span class |
| `items[].preserved_text` | original span text |

## Rules for later ACIs

- Do not invent replacement lyrics for flagged spans.
- Do not treat `UNVERIFIED_MACHINE_TEXT` as established lyrics.
- Human review/approval is a later capability.
- Vocal isolation is still not authorized.
