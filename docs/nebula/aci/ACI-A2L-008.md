# ACI-A2L-008

APPROVED LYRIC ARTIFACT

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED; LOCKED SONG NOT APPROVED

Permanent copy of the Operator ACI. This execution adds explicit human approval and approved lyric artifacts. Machine lyrics never auto-approve.

## Constraints honored

- New branch `feature/aci-a2l-008-approved-lyrics` from `feature/aci-a2l-007-primary-faster-whisper` @ `d0b0983884889bf6e2b6c602362187f8a0a44c7a`.
- Implementation commit: `ae12419`.
- Transcription engine unchanged: faster-whisper / Whisper large-v3.
- Save does not approve. Approval requires `confirm=true`.
- Validation used fixture SHA `aci-a2l-008-fixture`, not the locked Jay song.
- Locked song remains NOT APPROVED. Approved TXT/JSON for that song: NOT CREATED.
- whisper-1 baseline was not overwritten.
- Locked song SHA-256 unchanged.
- Not merged. Not pushed.

## Explicitly out of scope

Frontend application shell, additional transcription engines, vocal isolation, LLM lyric correction, music distribution, copyright/publishing workflows, unrelated export formats.
