# ACI-A2L-REL-001

SONG RELEASE RECORD

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED

Permanent copy of the Operator ACI. This execution adds a per-song release Current Truth record. It does not release or distribute the song.

## Constraints honored

- New branch `feature/aci-a2l-rel-001-song-release-record` from `deployable` @ `18852ffd4db0eae611b0c1cff9609af93090d88d`.
- Reuses existing Operator-entered song title and artist. WAV filename is not the title.
- Track duration is derived from ingested audio metadata. Master audio and approved lyrics are referenced, not duplicated as a second lyric authority.
- Missing fields stay MISSING. ISRC is never generated.
- READY/INCOMPLETE is internal record completeness, not commercial release.
- Implemented in the existing operator application at http://127.0.0.1:8780/.
- `deployable` and `main` were not modified. Not merged. Not pushed.

## Explicitly out of scope

Album-wide management, track sequencing, UPC/ISRC generation, distributor or store integrations, copyright/PRO/publishing registration, royalty splits, artwork, marketing, scheduling.
