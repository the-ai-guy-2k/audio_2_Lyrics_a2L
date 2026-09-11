# ACI-A2L-016

METADATA-BASED EXPORT FILENAMES

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution names user-downloaded lyric files from operator-supplied song title and artist. Approved lyric content is not changed.

## Constraints honored

- New branch `feature/aci-a2l-016-export-filenames` from `feature/aci-a2l-015-release-readiness` @ `f9532c95dfd77c6cb7f4023a3d1d7623999a5dc5`.
- Implementation commit: `af300ab`.
- File naming only. Lyric words, stored title/artist, approval state, and canonical `approved_lyrics.txt` / `approved_lyrics.json` names are unchanged.
- User-entered metadata is authoritative. The WAV filename is not used as a title. Missing artist/title are not invented.
- Default both-fields name: `<Artist> - <Song Title>.txt`.
- Partial fallbacks: title only → `<Song Title>.txt`; artist only → `<Artist> - Lyrics.txt`; neither → `lyrics.txt`.
- Format suffixes: Plain Text and Structured Lyrics append ` - Plain Text` / ` - Structured Lyrics` before `.txt`.
- Filename sanitization is presentation-only (invalid characters, separators, reserved names, empty results).
- Internal derived artifacts under `approved_lyrics/exports/` keep stable names so provenance paths stay intact.
- Not merged. Not pushed.

## Explicitly out of scope

Lyric formatting changes, title/artist intake changes, new metadata fields, new export formats, frontend redesign, renaming canonical authority files, merge/push.
