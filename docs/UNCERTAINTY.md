# Uncertainty handling (ACI-ATL-003)

FLAG IT — DO NOT INVENT IT.

This stage consumes the ACI-ATL-002 transcription draft and surfaces uncertainty. It does not rewrite lyrics, approve lyrics, or isolate vocals.

## Input

`machine_transcription/transcription_draft.json`

```bash
python -m a2l uncertainty artifacts/ingest/<job_id>/machine_transcription/transcription_draft.json
```

## Method

Deterministic flag evaluation. No LLM.

| Class | Meaning |
| --- | --- |
| `REQUIRES_LATER_RESOLUTION` | Questionable machine text (low confidence, no-speech, hallucination/boilerplate, no-signal, chunk boundary, repeats) |
| `UNVERIFIED_MACHINE_TEXT` | Engine text without those flags. Still **not** approved lyrics |
| `ESTABLISHED_LYRICS` | Not produced by this ACI |

Authority boundary:

- mastered audio = AUTHORITATIVE SOURCE
- machine transcription = NON-AUTHORITATIVE DRAFT
- uncertainty flag = REQUIRES LATER RESOLUTION

Original `engine_text` is copied to `preserved_engine_text`. `rewritten_text` is always `null`.

## Output

```text
artifacts/ingest/<sha256>/uncertainty/
  uncertainty_report.json
  uncertainty_report.txt
```

Contract: [UNCERTAINTY_CONTRACT.md](UNCERTAINTY_CONTRACT.md)

## Not in this ACI

Lyric structuring, human review, approved lyric artifacts, vocal isolation.
