# ACI-A2L-014

SONG METADATA INTAKE

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds optional song title and artist intake so a finished lyric sheet can show identifying information without inventing it.

## Constraints honored

- New branch `feature/aci-a2l-014-song-metadata` from `feature/aci-a2l-013-approved-export-formatting` @ `1518c3c5ae32ba7261db68cf7ba6d40903b8b19d`.
- Implementation commit: `44a880d`.
- Fields: SONG TITLE and ARTIST only. Both optional.
- WAV filename is not the song title. Missing values are left empty.
- Metadata is stored independently from machine-generated lyrics (`song_metadata.json` at the ingest job) and copied onto the review and approved JSON.
- Approved lyric TEXT remains the lyric body. Metadata does not change lyric words.
- Title/artist may be corrected before approval. After approval they are frozen until explicit reopen/reapproval.
- Standard Lyric Sheet uses supplied metadata when present. PLAIN TEXT and STRUCTURED LYRICS keep their existing purposes.
- Works for faster-whisper / large-v3 and NVIDIA Parakeet / TDT-0.6B-V2.
- Not merged. Not pushed.

## Explicitly out of scope

Album, songwriter, publisher, copyright, ISRC, release dates, cover art, automatic lookup, external music databases, new engines, unrelated frontend redesign, merge/push.
