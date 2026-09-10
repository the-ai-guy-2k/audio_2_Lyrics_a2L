# Reviewed lyric draft contract (produced by ACI-A2L-006)

**Producer:** ACI-A2L-006  
**Inputs:** primary faster-whisper large-v3 structured lyric draft  
**Authority:** `NON_AUTHORITATIVE_REVIEWED_DRAFT`

Save does not approve lyrics. Authoritative approved lyrics are a separate ACI-A2L-008 artifact.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-A2L-006` |
| `authority` | `NON_AUTHORITATIVE_REVIEWED_DRAFT` while not approved; `HUMAN_REVIEW_PROVENANCE` when the active lyrics are APPROVED |
| `active_lyric_authority` | `NOT_APPROVED` or `AUTHORITATIVE_APPROVED_LYRICS` |
| `usable_as_approved_lyrics` | `false` until explicit approval; never true while `REQUIRES_REAPPROVAL` |
| `approval_status` | `NOT_APPROVED` until explicit approval |
| `lyric_state` | `DRAFT` before first save; `REVIEWED` after save; `REQUIRES_REAPPROVAL` after explicit reopen; `APPROVED` only with current approved files |
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
- After APPROVED, Save and further corrections are refused until explicit reopen.
- Reopen archives current approved files and sets `REQUIRES_REAPPROVAL`. It does not invent replacement lyrics.
- The review record is never the approved lyric artifact. When APPROVED, `authority` is `HUMAN_REVIEW_PROVENANCE` and `active_lyric_authority` is `AUTHORITATIVE_APPROVED_LYRICS`.
