# Approved lyric artifact (ACI-A2L-008)

Convert a human-reviewed lyric draft into an explicitly approved authoritative lyric artifact. Machine output never becomes approved automatically.

## State progression

```text
MACHINE DRAFT → HUMAN REVIEW / CORRECTION → REVIEWED → APPROVED
APPROVED → (explicit reopen) → REQUIRES_REAPPROVAL → APPROVED
```

Only explicit operator confirmation establishes APPROVED. Save does not approve. Reopen archives the current approved files instead of editing them in place.

## How the operator approves

1. Open `python -m a2l review` → `http://127.0.0.1:8765/`
2. Review and correct phrases. Save as needed. State stays **REVIEWED** or **REQUIRES_REAPPROVAL**.
3. Click **Mark lyrics APPROVED**.
4. Confirm the browser dialog.
5. The UI POSTs `/api/approve` with `{ "confirm": true }`.

`confirm` must be the JSON boolean `true`. Saving does not send this request.

To correct after approval: **Reopen for correction** (`POST /api/reopen` `{ "confirm": true }`). Current `approved_lyrics.txt` / `.json` are moved under `approved_lyrics/history/<timestamp>/`. State becomes **REQUIRES_REAPPROVAL**. Approve again after edits.

## Artifacts written after approval

```text
artifacts/ingest/<sha256>/a2l_pipeline/approved_lyrics/
  approved_lyrics.txt
  approved_lyrics.json
```

The TXT is clean lyric lines only: current `human_text` for non-gap rows, one phrase per line. It does not include timestamps, uncertainty flags, confidence, machine provenance labels, or review-interface metadata.

The JSON retains provenance: source SHA, transcription engine/model, approval state, approval event, and the approved text.

Existing audio, machine transcription, uncertainty, structured draft, and human-review files are not overwritten as a substitute for these artifacts. The review JSON is updated only to record that approval happened.

## Locked Jay song

ACI-A2L-009 Amendment 01: the locked song is **REQUIRES_REAPPROVAL** so the Operator can correct remaining errors. The first approval is archived under `approved_lyrics/history/`. Current canonical approved files are inactive until the Operator approves again.

Contract: [APPROVED_LYRICS_CONTRACT.md](APPROVED_LYRICS_CONTRACT.md)
