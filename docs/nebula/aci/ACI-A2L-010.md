# ACI-A2L-010

A2L APPLICATION FRONTEND

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds a usable operator-facing application around the validated A2L workflow.

## Constraints honored

- New branch `feature/aci-a2l-010-frontend` from `feature/aci-a2l-009-real-song-validation` @ `209569359f500cb8986743a5cb603ca59b95807d`.
- Transcription engine unchanged: faster-whisper / Whisper large-v3.
- Review/provenance/approval/reopen behavior unchanged.
- Save is not approval. Approval requires `confirm=true`.
- UI tests used fixture WAV + ScriptedEngine. The locked Jay song was not approved or altered.
- Known leftover lyric cleanup from ACI-A2L-009 was not silently corrected.
- Not merged. Not pushed.

## Explicitly out of scope

New transcription engines, Parakeet, vocal isolation, automatic lyric correction, LLM rewriting, user accounts, authentication, cloud deployment, payments, distribution, copyright/publishing, extra export formats.
