# ACI-A2L-013 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-013 — Approved lyric export formatting  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (feature branch; not merged)

---

## Execution status

COMPLETE on bounded feature branch. After explicit approval, the operator application shows a Standard Lyric Sheet by default and allows Plain Text / Structured Lyrics presentations. Approved lyric words are unchanged. Canonical approved TXT/JSON remain authoritative.

Not merged. Not pushed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-013-approved-export-formatting` |
| Base | `feature/aci-a2l-012-nvidia-workflow` @ `7de34662cfb36e03e86a4dacab0bfc07e8b38565` |
| Implementation | `18bcd53` |

## Default output implementation

Approval writes canonical `approved_lyrics.txt` / `approved_lyrics.json`, then derived files under `approved_lyrics/exports/`. The operator UI treats APPROVED → Output as the next screen and loads STANDARD LYRIC SHEET without a format click.

`a2l/export.py` renders presentations from the approved artifact only. `ExportError NOT_APPROVED` refuses unapproved sessions.

## Available output choices

1. STANDARD LYRIC SHEET (`standard-lyric-sheet`) — default
2. PLAIN TEXT (`plain-text`)
3. STRUCTURED LYRICS (`structured-lyrics`)

## Preview / copy / download

| Action | Behavior |
| --- | --- |
| Preview | `GET /api/export?format=` fills the Output `<pre>`. Changing the selector reloads preview. |
| Copy | Copies the currently previewed formatted text. |
| Download | `GET /export/output.txt?format=` returns the selected presentation (`lyric-sheet.txt`, `lyrics.txt`, or `structured-lyrics.txt`). |
| Canonical | `GET /export/approved_lyrics.txt` and `.json` remain the authoritative files. |

## Authority / provenance

```text
SOURCE APPROVED ARTIFACT → SELECTED FORMAT → GENERATED EXPORT
```

Derived provenance records source TXT/JSON paths, format id, `DERIVED_EXPORT_PRESENTATION`, and `usable_as_approved_lyrics: false`. Reopen archives `exports/` with the prior approval.

Approved JSON now stores `lyric_lines` (text plus any pre-existing `section_label`) so Structured Lyrics can preserve labels without inventing them. Title/artist headers are emitted only from existing `song_title`/`title`/`artist` fields.

## Validation

| Check | Result |
| --- | --- |
| 1. Unapproved lyrics cannot generate authoritative final exports | PASS — `ExportError NOT_APPROVED`; `/api/export` 400 |
| 2. Approval exposes default Standard Lyric Sheet | PASS — UI navigates to Output; API default format is the sheet |
| 3. Standard Lyric Sheet selected by default | PASS — select `selected` + `DEFAULT_FORMAT` |
| 4. User can select another supported format | PASS |
| 5. Preview updates to selected format | PASS — format change calls `loadOutput()` |
| 6. Copy uses selected formatted output | PASS — copies `#output-preview` text |
| 7. Download/export uses selected format | PASS — `/export/output.txt?format=` |
| 8. Approved lyric words remain unchanged | PASS — formatter asserts word identity; locked-song bytes unchanged |
| 9. Canonical approved TXT/JSON preserved | PASS — derived files live under `exports/` |
| 10. Approval/reopen/reapproval remains functional | PASS — reopen archives exports; reapproval writes new ones |
| 11. Faster-whisper and Parakeet provenance supported | PASS — `tests/test_app.py` and `tests/test_parakeet_workflow.py` |
| 12. Applicable regression tests PASS | PASS — 91 tests |

## Applicable tests

`python -m pytest tests --ignore=tests/test_parakeet_candidate.py`

Result: **91 passed** (Python 3.14.3).

## Errors / warnings

Windows `Path.write_text` was translating `\n` to CRLF in approved TXT downloads. New approved TXT/JSON and derived exports are written with `newline="\n"` so canonical lyric files stay LF.

Current approved artifacts do not carry song title, artist, or section labels. The default sheet is therefore the approved lyric lines with no invented header or Verse/Chorus labels.

## Out of scope honored

No lyric rewrite, no LLM formatting, no invented sections, no engine-selection change, no publishing/copyright, no merge/push.

## Merge / push status

Not merged. Not pushed.

## Commit information

`18bcd53` on `feature/aci-a2l-013-approved-export-formatting` (implementation). Follow-up commit records this SHA in ACR-A2L-013.
