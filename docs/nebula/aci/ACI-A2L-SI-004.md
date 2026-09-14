# ACI-A2L-SI-004

KEY + MODE ENGINE CANDIDATE VALIDATION

AIW: CAE  
STATUS: EXECUTED ON FEATURE BRANCH — NOT MERGED — OPERATOR REVIEW REQUIRED

Permanent copy of the Operator ACI. This execution evaluates one commercially clean Key + Mode estimator on the locked Jay Garrett master. It does not estimate chords and does not create a Song Intelligence Record.

## Mission

Determine whether A2L can extract useful Key + Mode intelligence from the governed finished master on a normal consumer laptop.

## Constraints honored

- New branch `feature/aci-a2l-si-004-key-mode` from SI-003 `feature/aci-a2l-si-003-structure-resolution` @ `0a4f256`.
- Implementation commit: `fae5a3d`.
- Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged.
- Selected candidate: librosa `chroma_cqt` + Krumhansl-Schmuckler / Krumhansl-Kessler template correlation on the finished mix.
- Rejected: Essentia (AGPL/NC), madmom neural key models (NC weights).
- Isolated sidecar `.venv-key-mode` (Python 3.12). Not installed into Python 3.14 A2L.
- CPU only. No GPU. No cloud. No source separation.
- Results are MACHINE-DERIVED. Not written into approved lyrics or release authority.
- Not merged. Not pushed. Audio Intelligence not started.

## Explicitly out of scope

Chords, audio classification, genre/style, instrumentation, lyric intelligence, Song Intelligence Record, SI UI, mastering/QC, radio targeting, distributor logic.
