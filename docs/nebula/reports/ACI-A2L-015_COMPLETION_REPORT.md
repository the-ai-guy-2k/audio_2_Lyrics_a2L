# ACI-A2L-015 Completion Report

**Product:** Audio to Lyrics (A2L)  
**ACI:** ACI-A2L-015 — MVP release-readiness validation  
**AIW:** CAE  
**Date:** 2026-09-11  
**Recommendation:** **PASS** (feature-branch validated baseline; not merged)

---

## Execution status

COMPLETE on bounded feature branch. No product capability was added. The integrated operator workflow from upload through formatted output is usable. Authority rules remain intact. Locked Jay artifacts were not altered. Transcription was not rerun.

Not merged. Not pushed. Not deployed.

## Branch / commits

| Item | Value |
| --- | --- |
| Branch | `feature/aci-a2l-015-release-readiness` |
| Base | `feature/aci-a2l-014-song-metadata` @ `1f57a7eb1f60ace0a71501974ef498afcdd87dd3` |
| Implementation | `3ae25fb` |

## Supported application start

Primary extract (this workstation):

```bash
.venv-faster-whisper\Scripts\python.exe -m a2l app
```

**Application URL:** http://127.0.0.1:8780/

Details: [OPERATOR_START.md](../../OPERATOR_START.md)

Smoke this ACI: `python -m a2l app --host 127.0.0.1 --port 8799 --no-browser` on Python 3.14.3 → `GET /` 200, session JSON ok. Default Python 3.14.3 starts the UI and does not have faster-whisper; extract then reports the engine unavailable. That is expected isolation, not a silent failure.

## Integrated workflow validation

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Upload screen works | PASS | App HTML; `GET /` 200 |
| 2 | Valid WAV accepted | PASS | `tests/test_app.py`, `tests/test_ingest.py` |
| 3 | Invalid input rejected | PASS | `test_rejects_invalid_upload` |
| 4 | Song title optional | PASS | `tests/test_metadata.py`, `tests/test_app.py` |
| 5 | Artist optional | PASS | same |
| 6 | Missing metadata not invented | PASS | filename not used as title |
| 7 | Engine selectable | PASS | Upload selector; Parakeet workflow tests |
| 8 | faster-whisper / large-v3 functional | PASS | primary engine tests + locked-song provenance |
| 9 | NVIDIA Parakeet available | PASS | alternate path in app + `tests/test_parakeet_workflow.py`; not promoted |
| 10 | Processing status understandable | PASS | operator status strings in `app_server.py` |
| 11 | Transitions into lyric review | PASS | app session after extract |
| 12 | Paragraph-style review functional | PASS | `tests/test_review.py`, `tests/test_app.py` |
| 13 | Human corrections can be saved | PASS | save path |
| 14 | Save does not approve | PASS | export 400 until approve |
| 15 | Explicit human approval required | PASS | `confirm=true` |
| 16 | Approved state visible | PASS | `LYRIC STATE: APPROVED` |
| 17 | Approved lyrics can be reopened | PASS | reopen tests |
| 18 | Reopened lyrics require reapproval | PASS | `REQUIRES_REAPPROVAL`; export disabled |
| 19 | Standard Lyric Sheet default after approval | PASS | Output screen + default format |
| 20 | Output format can be changed | PASS | selector + `/api/export?format=` |
| 21 | Copy works or fallback | PASS | clipboard API with select-and-copy fallback (code inspection; live browser clipboard not clicked this ACI) |
| 22 | Download works | PASS | `/export/output.txt?format=` |
| 23 | Canonical TXT/JSON preserved | PASS | derived `exports/` are not substitutes |
| 24 | Original source WAV unchanged | PASS | ingest byte-identical copy; app tests keep source bytes |

## Engine governance

| Engine | Role | Status |
| --- | --- | --- |
| faster-whisper / Whisper large-v3 | PRIMARY | Functional. Isolated `.venv-faster-whisper` Python 3.12.10, faster-whisper 1.2.1. |
| NVIDIA Parakeet / TDT-0.6B-V2 | ALTERNATE | Available, not promoted. Isolated `.venv-parakeet` Python 3.12.10, nemo-toolkit import ok. Provenance remains `nvidia_nemo_parakeet` / `parakeet-tdt-0.6b-v2` under `a2l_pipeline_parakeet/`. |

## Authority validation

```text
MACHINE INTERPRETATION
  → HUMAN REVIEW
  → HUMAN CORRECTION
  → EXPLICIT HUMAN APPROVAL
  → AUTHORITATIVE APPROVED LYRICS
  → DERIVED OUTPUT PRESENTATION
```

| Rule | Result |
| --- | --- |
| Machine output never auto-authoritative | PASS |
| Save is not Approval | PASS |
| Formatting cannot modify approved lyric words | PASS |
| Derived exports are not authoritative replacements | PASS (`DERIVED_EXPORT_PRESENTATION`) |
| Reopen invalidates active approval until reapproval | PASS |
| Revision history remains traceable | PASS (Jay revision 2 + history dir) |

## Output / export validation

Default after approval: STANDARD LYRIC SHEET. PLAIN TEXT and STRUCTURED LYRICS remain selectable. Canonical `approved_lyrics.txt` / `approved_lyrics.json` unchanged by presentation. Unapproved sessions cannot export.

## Source-integrity validation

Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` matches `authoritative_source/source.wav`. Working WAV is byte-identical. whisper-1 and faster-whisper draft hashes unchanged vs prior ACIs. Approved TXT SHA-256 `8da23213e2d0b3fb62ae84a9d059b026117baf793e8cacbfc61db857ad2f476c` matches ACI-A2L-009 evidence. This ACI did not rewrite those files.

## Regression results

| Item | Value |
| --- | --- |
| Python | 3.14.3 |
| Command | `python -m pytest tests --ignore=tests/test_parakeet_candidate.py` |
| Result | **97 passed**, 0 failed |
| Ignored | `tests/test_parakeet_candidate.py` — untracked parked 005 helper, not in the tracked suite |
| Warnings | none material |

## Repository hygiene

Clean committed tree on this branch aside from validation records. Workstation still has **untracked parked files** that must not be committed at merge:

- `a2l.egg-info/`
- `docs/nebula/artifacts/aci-a2l-005-evidence/`
- `requirements-parakeet.txt`
- `scripts/run_parakeet_candidate.py`
- `tests/test_parakeet_candidate.py`

Tracked Parakeet/faster-whisper isolation docs remain: `requirements-nvidia-parakeet.txt`, `requirements-faster-whisper.txt`, `scripts/run_nvidia_parakeet_candidate.py`.

ACI-A2L-011 and ACI-A2L-012 have no ACR rows. That is historical, not a product defect.

Root `README.md` still describes an earlier capability set (through ACI-A2L-010) and still presents `python -m a2l app` without the isolated venv. Operator-accurate start is [OPERATOR_START.md](../../OPERATOR_START.md) and [FRONTEND.md](../../FRONTEND.md). Updating README is documentation follow-on, not this ACI.

## Documentation assessment

Present and sufficient for the MVP workflow: FRONTEND, SONG_METADATA, APPROVED_LYRICS, APPROVED_EXPORT, OPERATOR_START, engine requirement files, contracts, TRACEABILITY. Root README is stale relative to 012–014.

## Known limitations

- Local stdlib app only; not hosted.
- Primary extract requires the Python 3.12 faster-whisper venv on this workstation.
- Parakeet requires a separate 3.12 NeMo venv and substantial memory; it remains alternate.
- Engineering review page (`python -m a2l review` :8765) is a second UI and does not include title/artist intake.
- Locked Jay has no song title/artist (none were entered at approval).
- Known minor leftover lyric cleanup on Jay remains deferred (ACI-A2L-009); not a 015 blocker.
- Copy uses the browser clipboard API with a manual-select fallback.

## Blockers

None.

## Merge / push status

Not merged. Not pushed. Not deployed.

## Commit information

`3ae25fb` on `feature/aci-a2l-015-release-readiness` (validation records). Follow-up commit records this SHA in ACR-A2L-015.
