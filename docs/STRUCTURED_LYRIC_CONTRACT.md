# Structured lyric draft contract (produced by ACI-ATL-004)

**Producer:** ACI-ATL-004  
**Inputs:** ACI-ATL-002 transcription draft + ACI-ATL-003 uncertainty report

Downstream human review may consume this draft. It is not approved lyrics.

## Required fields

| Field | Meaning |
| --- | --- |
| `produced_by` | `ACI-ATL-004` |
| `authority` | `NON_AUTHORITATIVE_STRUCTURED_DRAFT` |
| `usable_as_approved_lyrics` | always `false` |
| `section_labels_assigned` | always `false` in this ACI |
| `preserved_engine_text` | unmodified engine text |
| `rewritten_text` | always `null` |
| `lines[].kind` | `machine_line` or `time_gap` |
| `lines[].preserved_text` | original span text (empty for gaps) |
| `lines[].status` | uncertainty class |
| `lines[].flags` | preserved plus `TIME_GAP` when applicable |
| `lines[].section_label` | always `null` in this ACI |

## Rules for later ACIs

- Do not treat structured lines as approved lyrics.
- Do not fill `time_gap` rows with guessed lyrics.
- Human review is ACI-A2L-006. Explicit approval is ACI-A2L-008.
- Vocal isolation is still not authorized.
