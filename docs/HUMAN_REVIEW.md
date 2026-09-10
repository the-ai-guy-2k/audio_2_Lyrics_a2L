# Human review and correction (ACI-A2L-006)

Review the primary faster-whisper large-v3 structured lyric draft. Correct machine errors. Preserve original machine text. The result is **not** approved lyrics.

## Open the interface

From the repository root:

```bash
python -m a2l review
```

Then open: `http://127.0.0.1:8765/`

## What you see

Lyrics display as wrapping paragraph text, not isolated machine-record rows.

- Uncertain phrases have an amber highlight in the paragraph
- Human-corrected phrases are underlined
- Click a phrase to edit it and to see original machine text and flags
- Time gaps are kept in the stored data but are not shown as separate reading rows

## Save

Save reviewed draft writes:

```text
artifacts/ingest/<sha256>/a2l_pipeline/human_review/
  reviewed_lyric_draft.json
  reviewed_lyric_draft.txt
```

Contract: [REVIEW_CONTRACT.md](REVIEW_CONTRACT.md)

## Not in this ACI

Authoritative approval, APPROVED state, final lyric export, vocal isolation, LLM rewrite.
