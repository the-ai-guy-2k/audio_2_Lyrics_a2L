# ACI-A2L-SI-008

AUDIO INTELLIGENCE CLASSIFICATION RESOLUTION

AIW: CAE  
STATUS: APPROVED ACI EXECUTED ON FEATURE BRANCH — NOT MERGED — OPERATOR / JAY REVIEW REQUIRED

Permanent copy of the Operator ACI (APPROVED FOR EXECUTION). This diagnostic resolves SI-007 classification discrimination without reopening Energy / Intensity and without replacing CLAP.

## Mission

Determine why SI-007 CLAP rankings were weakly separated for Instrumentation, Genre/Style, Vocal, and Acoustic/Electronic, and whether a technically valid prompt/aggregation strategy can make those categories useful.

## Constraints honored

- New branch `feature/aci-a2l-si-008-audio-classification-resolution` from SI-007 `feature/aci-a2l-si-007-audio-intelligence` @ `6e94bad`.
- Implementation commit recorded after commit.
- Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged.
- Same checkpoint: `laion/larger_clap_music` revision `a0b4534a14f58e20944452dff00a22a06ce629d1`. Complete local weights reused. No new CLAP download.
- CONTROL = exact SI-007 method (EOS text, mean-pooled 10s audio, original templates, cosine ranking).
- RESOLUTION selected per category by highest `top_margin` (rank-1 minus rank-2 cosine), not by a preferred label.
- Equivalent prompt treatment within each category. No Jay/artist/genre hints.
- Hugging Face `ClapTextPooler` was diagnostic-only and was not used as the selected path.
- Energy / Intensity was not reopened. SI-007 evidence was not modified.
- CPU only. GPU not required. Cloud not required.
- Not merged. Not pushed. Song Intelligence Record not created.

## Diagnostic causes recorded

- A formulation: modest winner/margin change; not enough for instrumentation or genre WIN.
- B embedding: pooler pairwise cosine ~0.999 (collapsed); EOS pairwise ~0.80–0.86 (usable).
- C scoring: softmax remains uninformative; cosine `top_margin` / `spread` are the reported metrics.
- D aggregation: per-window mean cosine ≈ whole-song mean pool; mean pooling did not destroy the signal.
- E unsuitability: unique-label instrumentation and genre remain STILL WEAK on this checkpoint.

## Explicitly out of scope

Song Intelligence Record, SI UI, lyrics, retranscription, master mutation, engines #1/#2/#4, Energy, chords, QC, source separation, marketing, radio, distributor, replacing CLAP with another heavyweight model.
