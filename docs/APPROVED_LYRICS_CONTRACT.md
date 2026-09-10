# Approved lyrics contract (produced by ACI-A2L-008)

**Producer:** ACI-A2L-008  
**Inputs:** ACI-A2L-006 reviewed lyric draft  
**Authority:** `AUTHORITATIVE_APPROVED_LYRICS`

Created only after `approve_reviewed_lyrics(..., confirm=True)`.

## Files

| File | Contents |
| --- | --- |
| `approved_lyrics.txt` | Clean approved lyric body only |
| `approved_lyrics.json` | Provenance plus the same approved text |

## JSON required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-A2L-008` |
| `authority` | `AUTHORITATIVE_APPROVED_LYRICS` |
| `approval_status` | `APPROVED` |
| `usable_as_approved_lyrics` | `true` |
| `source_sha256` | ingest job / source identity |
| `transcription_engine` | engine recorded on the review |
| `transcription_model` | model recorded on the review |
| `approval_event.method` | `EXPLICIT_CONFIRM` |
| `approval_event.automatic` | `false` |
| `approval_event.approved_by` | `OPERATOR` |
| `approved_lyric_text` | same body as the TXT |

## Rules

- `confirm is not True` → `APPROVAL_NOT_EXPLICIT`. No files written.
- Save, transcription, uncertainty, and structuring never write these files.
- Clean TXT omits `time_gap` rows and processing clutter.
- `machine_text` remains on the review JSON; it is not copied into the clean TXT.
- After APPROVED, further Save/corrections are refused (`ALREADY_APPROVED`).
- Display state is APPROVED only when review flags and both files exist.
