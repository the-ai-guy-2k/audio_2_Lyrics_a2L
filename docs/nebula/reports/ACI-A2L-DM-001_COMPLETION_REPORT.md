# ACI-A2L-DM-001 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-DM-001 — Song Object Model  
**AIW:** CAE  
**Date:** 2026-09-15  
**Recommendation:** **PASS** (feature branch; not promoted)

---

## Execution status

COMPLETE on `feature/aci-a2l-dm-001-song-object-model`. Canonical Song Object Model v1 is defined and documented. Optional JSON Schema companion added. Existing product artifacts and UI were not modified. Not promoted.

## Baseline

| Item | Value |
| --- | --- |
| Base `deployable` / `main` | `d5e3c85ed128a8fdc124adaa2dee7c150d3da311` |
| Branch | `feature/aci-a2l-dm-001-song-object-model` @ `98eac80` |
| Canonical model | `docs/nebula/data-model/A2L_SONG_OBJECT_MODEL_V1.md` |
| Schema companion | `docs/nebula/data-model/a2l_song_object_model_v1.schema.json` |
| Record type (future) | `A2L_SONG` |
| Schema version | `1.0.0` |

## Inspection summary (repository truth)

| Area | Current truth used |
| --- | --- |
| Ingest / source | `artifacts/ingest/<sha256>/` with `ingest_manifest.json`, `authoritative_source/source.wav`; job id equals source SHA today |
| Metadata | `song_metadata.json` — operator title/artist; filename never title |
| Approved lyrics | `a2l_pipeline/approved_lyrics/` (authority boundary human approval) |
| SIR | `song_intelligence_record.json` + `song_intelligence_record_history/` |
| Release | `song_release_record.json` |
| Album | `artifacts/releases/<release_id>/album_release_manifest.json` stores `ingest_job_id` + position only |
| Temporary SI UI | `song_intelligence_ui/ui_aggregation.json` — derived; does not outrank SIR |

## Validation

| # | Requirement | Result |
| --- | --- | --- |
| 1 | Song with a master WAV | PASS — mapped via `source.masters[]` / ingest paths |
| 2 | Song with approved lyrics | PASS — Jay approved lyrics referenced; authority preserved |
| 3 | Song with a SIR | PASS — Jay SIR revision 1 referenced |
| 4 | Four intelligence domains | PASS — rhythm_structure, key_mode, audio_intelligence, lyric_intelligence |
| 5 | Partial intelligence | PASS — Jay audio PARTIAL; rhythm UNAVAILABLE preserved |
| 6 | Missing metadata | PASS — model requires explicit MISSING; no filename inference |
| 7 | Existing release information | PASS — Jay release INCOMPLETE + missing required fields preserved |
| 8 | Album relationship without Album authority copy | PASS — reference `release_id` / position only |
| 9 | Same Song + future new master | PASS — `masters[]` CURRENT/SUPERSEDED relationship defined |
| 10 | Existing artifacts without destructive migration | PASS — docs only; Jay artifacts not modified |

Jay master SHA-256 verified present as governed ingest identity:

`bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be`

Documentation links target existing repo docs (`SONG_METADATA`, `SONG_INTELLIGENCE_RECORD`, `SONG_RELEASE_RECORD`, `ALBUM_RELEASE_MANIFEST`, `FIXED_TEST_SONG`, architecture).

## Explicitly not done

Song Registry, Album Object, Artist Object, UI changes, ingest rewrite, analyzer repair, lyric/SIR/release authority changes, promotion, master-replacement automation.

---

## Minority Report

WHAT IS BEING DONE: `song_id` is defined as an opaque future registry identifier and is intentionally **not** equal to today's `ingest_job_id` / source SHA-256, even though the current product uses that SHA as the only stable song key.  
WHY IT MATTERS: Equating Song identity to master bytes would force every remaster into a new Song and block the required same-Song / multi-master relationship.  
PA IMPACT: NONE for current product operation (registry not implemented; ingest paths unchanged). Future registry work must bridge existing ingest jobs without rewriting SHA-based storage.  
DISPOSITION: ACCEPTED MODEL DECISION — deferred assignment; documented incompatibility of SHA-as-Song-id with multi-master intent.

WHAT IS BEING DONE: Song intelligence/release/lyrics are modeled as **references** to existing governed artifacts rather than duplicated values inside a new Song store.  
WHY IT MATTERS: Duplication would create competing authority and break ACI constraints on lyric/SIR/release truth.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL

WHAT IS BEING DONE: No database or storage migration is introduced by this ACI.  
WHY IT MATTERS: Product continues on filesystem ingest/release artifacts.  
PA IMPACT: NONE  
DISPOSITION: INFORMATIONAL
