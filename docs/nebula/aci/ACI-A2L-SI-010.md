# ACI-A2L-SI-010

INSTRUMENTATION FINAL RESOLUTION

AIW: CAE  
STATUS: APPROVED ACI EXECUTED ON FEATURE BRANCH — NOT MERGED — OPERATOR / JAY REVIEW REQUIRED  
REPAIR ATTEMPT: 3 OF 3 FINAL

Permanent copy of the Operator ACI (APPROVED FOR EXECUTION). This execution evaluates ONE specialized instrument-presence candidate after SI-009 left Instrumentation NO WIN. It does not reopen genre, energy, acoustic/electronic, vocals, or CLAP, and it does not retune AST.

## Mission

Determine whether one commercially acceptable, CPU-first pretrained instrument-presence analyzer can produce useful instrumentation evidence from the locked Jay Garrett master.

Authorized capability only:

FINISHED MASTER WAV → SPECIALIZED INSTRUMENT-PRESENCE ANALYSIS → USEFUL INSTRUMENTATION EVIDENCE

## Constraints honored

- New branch `feature/aci-a2l-si-010-instrumentation-final-resolution` from SI-009 `feature/aci-a2l-si-009-instrumentation-genre-resolution` @ `627aeb0`.
- Selected candidate: PANNs Cnn14 (`Cnn14_mAP=0.431.pth`, Zenodo 3987831). Audio tagging / independent multi-label presence, not a genre classifier.
- Model license verified independently of library license: Zenodo metadata `license.id = cc-by-4.0`. Code MIT (`qiuqiangkong/audioset_tagging_cnn`, `torchlibrosa`).
- Isolated sidecar reuse of `.venv-clap`. Not installed into Python 3.14 A2L. Cache `%USERPROFILE%\.cache\a2l-panns`.
- CPU only. GPU not required. No cloud inference. Zenodo used only for first-time weight distribution (327,428,481 bytes, md5 `541141fa2ee191a88f24a3219fff024e`).
- Native AudioSet instrument subset. SI-007 CLAP vocabulary was not forced. SI-009 AST 0.15 threshold was not changed. AST was not rerun.
- Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged.
- Not merged. Not pushed. Song Intelligence Record not created. No fourth repair ACI.

## Category result (engineering)

- Instrumentation: PARTIAL (Guitar clipwise_mean 0.1705 / max 0.7221; operating_point 0.50; strong_count=0)
- ENGINE #3 FINAL: PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD
- MUSICAL VALIDATION: PENDING JAY
- REPAIR BUDGET: EXHAUSTED
- Known defect: INSTRUMENTATION INTELLIGENCE UNRESOLVED → bug-fix lane

## Explicitly out of scope

Song Intelligence Record, SI UI, lyrics, retranscription, master mutation, engines #1/#2/#4, Energy, genre, acoustic/electronic, vocals, CLAP diagnostics, AST retune, chords, QC, user-facing source separation, training/fine-tuning, marketing, radio, distributor, merge, promote, SI-011 instrumentation repair.
