# Approved lyric artifact (ACI-A2L-008)

Convert a human-reviewed lyric draft into an explicitly approved authoritative lyric artifact. Machine output never becomes approved automatically.

## State progression

```text
MACHINE DRAFT → HUMAN REVIEW / CORRECTION → REVIEWED → APPROVED
```

Only explicit operator confirmation establishes APPROVED. Transcription, uncertainty, structuring, saving edits, and loading the review UI do not approve lyrics.

## How the operator approves

1. Open `python -m a2l review` → `http://127.0.0.1:8765/`
2. Review and correct phrases. Save as needed. State stays **REVIEWED**.
3. Click **Mark lyrics APPROVED**.
4. Confirm the browser dialog.
5. The UI POSTs `/api/approve` with `{ "confirm": true }`.

`confirm` must be the JSON boolean `true`. Saving does not send this request.

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

The locked test song remains **NOT APPROVED**. Do not click Approve on that draft to prove the button. Automated tests use fixture SHA `aci-a2l-008-fixture`.

Contract: [APPROVED_LYRICS_CONTRACT.md](APPROVED_LYRICS_CONTRACT.md)
