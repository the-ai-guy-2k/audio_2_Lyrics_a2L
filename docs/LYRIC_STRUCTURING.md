# Lyric structuring (ACI-ATL-004)

Structuring turns uncertainty-annotated machine spans into a lyric draft for human review.

Structuring is **not** rewriting. Words are not corrected. Uncertain spans stay flagged. The result is **not** approved lyrics.

## Input

- `machine_transcription/transcription_draft.json` (ACI-ATL-002)
- `uncertainty/uncertainty_report.json` (ACI-ATL-003)

```bash
python -m a2l structure artifacts/ingest/<job_id>/uncertainty/uncertainty_report.json
```

## Method

Each uncertainty item becomes a timed `machine_line` with the original `preserved_text`, status, and flags.

- No verse/chorus labels (that would guess song form).
- Time gaps ≥ 2 seconds become `time_gap` rows with empty text and `TIME_GAP`. Lyrics are not invented for those regions.
- `rewritten_text` is always `null`.
- `usable_as_approved_lyrics` is always `false`.

## Output

```text
artifacts/ingest/<sha256>/structured_lyrics/
  structured_lyric_draft.json
  structured_lyric_draft.txt
```

Contract: [STRUCTURED_LYRIC_CONTRACT.md](STRUCTURED_LYRIC_CONTRACT.md)

## Not in this ACI

Human review, approval, approved lyric artifacts, vocal isolation.
