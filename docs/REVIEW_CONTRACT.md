# Reviewed lyric draft contract (produced by ACI-A2L-006)

**Producer:** ACI-A2L-006  
**Inputs:** faster-whisper large-v3 structured lyric draft  
**Authority:** `NON_AUTHORITATIVE_REVIEWED_DRAFT`

This is not approved lyrics.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-A2L-006` |
| `authority` | `NON_AUTHORITATIVE_REVIEWED_DRAFT` |
| `usable_as_approved_lyrics` | always `false` |
| `approval_status` | `NOT_APPROVED` |
| `transcription_engine` | `faster-whisper` |
| `transcription_model` | `large-v3` |
| `lines[].machine_text` | original machine line; never overwritten |
| `lines[].human_text` | current reviewed text |
| `lines[].text_source` | `MACHINE` or `HUMAN_CORRECTED` |

## Rules

- Do not treat reviewed text as approved lyrics.
- Do not silently replace `machine_text`.
- Do not fill `time_gap` rows with invented lyrics.
- Human approval is a later capability.
