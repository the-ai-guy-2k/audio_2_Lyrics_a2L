# ACI-A2L-007

PROMOTE FASTER-WHISPER LARGE-V3 TO PRIMARY TRANSCRIPTION ENGINE

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED; LYRICS NOT APPROVED

Permanent copy of the Operator ACI. This execution promotes the validated faster-whisper / Whisper large-v3 candidate into the primary A2L transcription path.

## Constraints honored

- New branch `feature/aci-a2l-007-primary-faster-whisper` from `feature/aci-a2l-006-human-review` @ `a637323`.
- Did not branch from parked Parakeet work.
- `python -m a2l transcribe` uses faster-whisper / Whisper large-v3.
- Historical whisper-1 artifacts were not overwritten.
- Same locked WAV: `01Stomp to MIX MSTR 24bit_48hz.wav`
- SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`
- Uncertainty, structuring, and human review consume the primary draft without candidate-specific copying.
- Not merged. Not pushed.

## Explicitly out of scope

Frontend application shell, final lyric approval, final export, new transcription engines, Parakeet, vocal isolation, LLM lyric reconstruction.
