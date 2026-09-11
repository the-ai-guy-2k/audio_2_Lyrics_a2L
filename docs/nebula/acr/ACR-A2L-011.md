# ACR-A2L-011 — ACI-A2L-011 acceptance

**ACI:** ACI-A2L-011 — NVIDIA transcription engine candidate evaluation  
**Date recorded:** 2026-09-11 (traceability restored from existing repository evidence; execution was 2026-09-11)  
**Branch:** `feature/aci-a2l-011-nvidia-candidate`  
**Commit:** `7f3ae80`  
**Status:** EXECUTED on feature branch — candidate only; not promoted; quality winner not decided  
**Product changes:** none to the primary path. Isolated Parakeet candidate artifacts only.

## Accepted outcome (from existing evidence)

NVIDIA Parakeet TDT 0.6B v2 was run as an isolated candidate on the locked Jay master. The candidate completed on CPU. Source SHA was unchanged. Primary `a2l_pipeline`, approved lyrics, whisper-1, and faster-whisper artifacts were not overwritten. Parakeet was not promoted and was not approved.

This ACR does not invent a quality verdict. Operator quality review of the candidate lyrics remains outside CAE.

NVIDIA PARAKEET CANDIDATE RUN: EXECUTED  
PRIMARY ENGINE REPLACED: NO  
PROMOTED: NO

## Evidence (in repo; not invented)

- `docs/nebula/aci/ACI-A2L-011.md`
- `docs/nebula/artifacts/aci-a2l-011-evidence/README.md`
- `docs/nebula/artifacts/aci-a2l-011-evidence/nvidia_parakeet_lyrics.txt`
- `docs/nebula/artifacts/aci-a2l-011-evidence/nvidia_parakeet_run.json`
- `docs/nebula/artifacts/aci-a2l-011-evidence/nvidia_parakeet_raw.json`
- Implementation commit `7f3ae80`; record commit `465438b`

## Gaps

- No original ACR was written at execution time; this record restores ACI↔ACR linkage from the evidence already in the repository.
- There is no ACI-A2L-011 completion report in-tree.
- Candidate quality was not decided by CAE.
