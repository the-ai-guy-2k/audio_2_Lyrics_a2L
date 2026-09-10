# ACI-ATL-002 handoff contract

**Producer:** ACI-ATL-001  
**Consumer:** ACI-ATL-002 — Direct mastered-WAV transcription baseline  
**Schema:** `ingest_manifest.json` `schema_version` = `1.0.0`

ACI-ATL-002 must not infer undocumented behavior. Consume the files and fields below.

## What to consume

For a completed ingest job at `artifacts/ingest/<job_id>/`:

1. Read `ingest_manifest.json`.
2. Use `derived_working.relative_path` as the transcription input.
3. Treat `authoritative_source.relative_path` as read-only CONTROL evidence. Do not overwrite it.

Absolute paths are not part of the contract. Resolve relative paths against the job directory that contains the manifest.

## Required manifest fields

| Field | Meaning |
| --- | --- |
| `produced_by` | Always `ACI-ATL-001` |
| `intended_consumer` | `ACI-ATL-002` |
| `job_id` | SHA-256 of the source WAV bytes |
| `control_baseline` | `CONTROL_A` |
| `authoritative_source.role` | `AUTHORITATIVE_SOURCE` |
| `authoritative_source.sha256` | Digest of `source.wav` |
| `authoritative_source.immutable` | `true` |
| `derived_working.role` | `DERIVED_WORKING` |
| `derived_working.sha256` | Digest of `transcription_ready.wav` |
| `derived_working.byte_identical_to_source` | `true` for this ACI |
| `derived_working.preprocessing` | `none` |
| `derived_working.vocal_isolation` | `not_applied` |
| `derived_working.transcription_ready` | `true` (validated WAV, untreated) |
| `audio.file_format` | `WAV` |
| `audio.duration_seconds` | `nframes / sample_rate` |
| `audio.sample_rate_hz` | Source rate. **Do not assume 16000.** |
| `audio.channel_count` | Source channels. **Do not assume mono.** |

## Assumptions ACI-ATL-002 must not make

- Sample rate is **not** converted to 16 kHz or any other rate.
- Channels are **not** mixed to mono.
- Loudness is **not** normalized.
- Vocals are **not** isolated.
- The working file is **not** a stem. It is the mastered mix, byte-identical to source.
- Transcription has **not** been run.

If ACI-ATL-002 needs a different control (normalized audio or isolated vocals), that is a later ACI. This handoff is CONTROL A only.

## CLI result shape (optional)

`python -m a2l ingest <wav> --artifact-root artifacts` prints JSON on stdout with `manifest_path`, `authoritative_source`, `derived_working`, `audio`, and `control_baseline`. The manifest file is the durable contract; CLI JSON is a convenience.

## Example job layout

```text
artifacts/ingest/<sha256>/
  ingest_manifest.json
  authoritative_source/source.wav
  derived_working/transcription_ready.wav
```
