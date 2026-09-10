# Reviewed lyric draft contract (produced by ACI-A2L-006)

**Producer:** ACI-A2L-006  
**Inputs:** primary faster-whisper large-v3 structured lyric draft  
**Authority:** `NON_AUTHORITATIVE_REVIEWED_DRAFT`

Save does not approve lyrics. Authoritative approved lyrics are a separate ACI-A2L-008 artifact.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-A2L-006` |
| `authority` | `NON_AUTHORITATIVE_REVIEWED_DRAFT` |
| `usable_as_approved_lyrics` | `false` until explicit ACI-A2L-008 approval |
| `approval_status` | `NOT_APPROVED` until explicit ACI-A2L-008 approval |
| `lyric_state` | `DRAFT` before first save; `REVIEWED` after save; `APPROVED` only after ACI-A2L-008 |
| `transcription_engine` | `faster-whisper` |
| `transcription_model` | `large-v3` |
| `lines[].machine_text` | original machine line; never overwritten |
| `lines[].human_text` | current reviewed text |
| `lines[].text_source` | `MACHINE` or `HUMAN_CORRECTED` |

## Rules

- Do not treat a saved reviewed draft as approved lyrics.
- Do not silently replace `machine_text`.
- Do not fill `time_gap` rows with invented lyrics.
- `save_review` always writes `NOT_APPROVED`.
- Explicit approval (ACI-A2L-008) updates this JSON to record APPROVED and writes separate `approved_lyrics.txt` / `approved_lyrics.json`.
- After APPROVED, Save and further corrections are refused.
