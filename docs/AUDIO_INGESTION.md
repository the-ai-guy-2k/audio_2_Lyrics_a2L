# A2L audio ingestion (ACI-ATL-001)

This document is the product description of the ingestion capability. The machine contract for the next ACI is [ACI_ATL_002_HANDOFF.md](ACI_ATL_002_HANDOFF.md).

## Purpose

Accept a real mastered WAV as the authoritative source, validate it, preserve it unchanged, record technical metadata, and produce a deterministic transcription-ready working artifact.

## Required input

- Format: uncompressed PCM WAV (`RIFF` / `WAVE`)
- Codec: uncompressed PCM only
- Delivery: local filesystem path

Unsupported: MP3, AAC, FLAC, AIFF, text, empty files, truncated/corrupt WAV, compressed WAV codecs.

## Artifact distinction

| Role | Path under `artifacts/ingest/<sha256>/` | Mutability |
| --- | --- | --- |
| AUTHORITATIVE SOURCE | `authoritative_source/source.wav` | Immutable after first write |
| DERIVED WORKING | `derived_working/transcription_ready.wav` | Working copy for downstream ACIs |

`job_id` is the SHA-256 of the source bytes. Repeat ingest of the same file reuses the same job directory and does not rewrite the authoritative source.

## Working-artifact policy (CONTROL A)

The derived working file is a byte-identical copy of the authoritative source.

Explicitly **not** applied:

- peak / loudness normalization
- resampling
- channel mixdown
- vocal isolation / Demucs / stem separation
- transcription

This is intentional. Future experiments may compare:

- CONTROL A — mastered WAV directly (this artifact)
- CONTROL B — preprocessed/normalized audio
- CONTROL C — isolated vocal stem

CONTROL B and CONTROL C are **not** produced by ACI-ATL-001. Vocal isolation is an open architectural question and is not mandatory.

## Metadata recorded

`ingest_manifest.json` always includes:

- `audio.file_format`
- `audio.duration_seconds`
- `audio.sample_rate_hz`
- `audio.channel_count`

Plus container, codec, sample width, frame count, byte size, and SHA-256 for both artifacts.

## Failure behavior

Invalid input raises `IngestionError` and the CLI exits `2` with JSON on stderr:

```json
{"ok": false, "error_code": "UNSUPPORTED_FORMAT", "error": "..."}
```

Codes: `NOT_FOUND`, `NOT_A_FILE`, `EMPTY_INPUT`, `UNSUPPORTED_FORMAT`, `CORRUPT_WAV`, `UNSUPPORTED_CODEC`, `INVALID_WAV`, `EMPTY_AUDIO`, `READ_FAILED`.

No job directory is created for a failed ingest of a new file.

## Determinism

Same source bytes → same `job_id`, same working WAV bytes, same manifest JSON (sorted keys, no wall-clock fields).
