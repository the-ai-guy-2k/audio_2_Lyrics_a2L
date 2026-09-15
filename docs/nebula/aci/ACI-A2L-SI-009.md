# ACI-A2L-SI-009

INSTRUMENTATION & GENRE RESOLUTION CANDIDATE

AIW: CAE  
STATUS: APPROVED ACI EXECUTED ON FEATURE BRANCH — NOT MERGED — OPERATOR / JAY REVIEW REQUIRED  
REPAIR ATTEMPT: 2 OF 3

Permanent copy of the Operator ACI (APPROVED FOR EXECUTION). This execution evaluates ONE specialized music-tagging candidate for Instrumentation and Genre / Style after SI-008 left those CLAP categories NO WIN. It does not continue CLAP prompt engineering and does not replace CLAP Energy / Acoustic / Vocal results.

## Mission

Determine whether one commercially acceptable, CPU-first pretrained music tagger can produce useful instrumentation and genre/style evidence from the locked Jay Garrett master.

Authorized capability only:

FINISHED MASTER WAV → SPECIALIZED MUSIC-TAGGING ANALYZER → INSTRUMENTATION + GENRE/STYLE EVIDENCE

## Constraints honored

- New branch `feature/aci-a2l-si-009-instrumentation-genre-resolution` from SI-008 `feature/aci-a2l-si-008-audio-classification-resolution` @ `1b61291`.
- Selected candidate: Hugging Face `transformers` `ASTForAudioClassification` with `MIT/ast-finetuned-audioset-10-10-0.4593` revision `f826b80d28226b62986cc218e5cec390b1096902`.
- Model/checkpoint license verified independently of the library license: Hugging Face card `license: bsd-3-clause`; original AST repo BSD 3-Clause (Yuan Gong, 2021). AudioSet dataset CC BY 4.0; ontology CC BY-SA 4.0 (native class names emitted; ontology not adapted).
- Software: Apache-2.0 (transformers, huggingface_hub); BSD-style (torch); ISC (librosa).
- Isolated sidecar reuse of `.venv-clap` (Python 3.12.10, transformers 4.44.2, torch 2.14.0+cpu). Not installed into Python 3.14 A2L. Separate model cache `~/.cache/a2l-ast`.
- CPU only. GPU not required. No cloud inference. Hugging Face Hub used only for first-time weight distribution (~346 MB `model.safetensors`).
- Native AudioSet 527-class sigmoid scores preserved. SI-007 CLAP vocabulary was not forced. Documented instrument groups use max(member scores) only as supplementary mapping.
- Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged. Derived in-memory 16 kHz mono resample only.
- CLAP was not rerun. Comparison used preserved SI-008 evidence.
- Energy / Intensity, Acoustic / Electronic, and Vocal Characteristics were not reopened.
- Not merged. Not pushed. Song Intelligence Record not created. Repair Attempt 3 was not started.

## Category results (engineering)

- Instrumentation: NO WIN (Guitar 0.0654 / Plucked string 0.0512; top_margin=0.0142; no tag ≥ 0.15)
- Genre / Style: WIN (Grunge 0.1673 / Independent music 0.1099; top_margin=0.0573)
- ENGINE #3: PARTIAL PASS
- MUSICAL VALIDATION: PENDING JAY

## Explicitly out of scope

Song Intelligence Record, SI UI, lyrics, retranscription, master mutation, engines #1/#2/#4, Energy, CLAP prompt engineering, chords, QC, source-separation product path, training/fine-tuning, marketing, radio, distributor, merge, promote, Repair Attempt 3.
