# Human review and correction (ACI-A2L-006)

Review the primary faster-whisper large-v3 structured lyric draft. Correct machine errors. Preserve original machine text. Saving a review does **not** approve lyrics.

The **product-facing** operator application is `python -m a2l app` at http://127.0.0.1:8780/. This page is the engineering review interface.

## Open the interface

From the repository root:

```bash
python -m a2l review
```

Then open: `http://127.0.0.1:8765/`

Restart this process after code changes so `/api/approve` and `/api/reopen` are loaded.

## What you see

Lyrics display as wrapping paragraph text, not isolated machine-record rows.

- Uncertain phrases have an amber highlight in the paragraph
- Human-corrected phrases are underlined
- Click a phrase to edit it and to see original machine text and flags
- Time gaps are kept in the stored data but are not shown as separate reading rows
- The page shows `LYRIC STATE: DRAFT | REVIEWED | REQUIRES_REAPPROVAL | APPROVED`

## Save

Save reviewed draft writes:

```text
artifacts/ingest/<sha256>/a2l_pipeline/human_review/
  reviewed_lyric_draft.json
  reviewed_lyric_draft.txt
```

Save never creates `approved_lyrics.txt` or `approved_lyrics.json`.

Contract: [REVIEW_CONTRACT.md](REVIEW_CONTRACT.md)

## Approval

Approval is a separate explicit action (ACI-A2L-008). After approval, **Reopen for correction** archives the current approved files and returns the draft to `REQUIRES_REAPPROVAL`. Details: [APPROVED_LYRICS.md](APPROVED_LYRICS.md)

## Not in this ACI

Vocal isolation, LLM rewrite, finished application frontend.
