# ACI-A2L-013

APPROVED LYRIC EXPORT FORMATTING

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution formats already-approved lyrics for reading, copy, and download. Authoritative approved lyric content is not rewritten.

## Constraints honored

- New branch `feature/aci-a2l-013-approved-export-formatting` from `feature/aci-a2l-012-nvidia-workflow` @ `7de34662cfb36e03e86a4dacab0bfc07e8b38565`.
- Input is `AUTHORITATIVE_APPROVED_LYRICS` only. Unapproved lyrics cannot generate formatted exports.
- Approved lyric words are not corrected, rewritten, or inferred.
- Canonical `approved_lyrics.txt` / `approved_lyrics.json` remain authoritative. Derived files are not a substitute.
- Default operator output after approval is STANDARD LYRIC SHEET.
- Song title/artist appear only when already present on the approved artifact. Missing metadata is not invented. WAV filenames are not treated as titles.
- Verse / Chorus / Bridge labels appear only when `section_label` already exists on approved lyric lines. Labels are not invented for presentation.
- Works for approved lyrics from faster-whisper / large-v3 and NVIDIA Parakeet / TDT-0.6B-V2. Engine selection is unchanged.
- No LLM formatting. No publishing/distribution. No copyright registration.
- Not merged. Not pushed.

## Explicitly out of scope

Lyric rewriting, automatic correction, invented song sections, transcription-engine changes, unrelated frontend redesign, publishing integrations, copyright registration, merge/push.
