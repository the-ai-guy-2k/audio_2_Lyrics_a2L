# ACI-A2L-009 evidence

Real-song end-to-end validation after explicit Operator approval.

- `approved_lyrics.txt` / `approved_lyrics.json` — copies of the Operator-approved artifacts
- `runtime_validation.json` — SHA checks, counts, approval event

Runtime originals (gitignored ingest tree):

```text
artifacts/ingest/<sha>/a2l_pipeline/approved_lyrics/
  approved_lyrics.txt
  approved_lyrics.json
```

Machine transcription and human-review files remain beside those approved artifacts. They were not replaced.
