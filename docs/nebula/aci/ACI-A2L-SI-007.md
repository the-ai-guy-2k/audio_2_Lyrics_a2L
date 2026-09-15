# ACI-A2L-SI-007

AUDIO INTELLIGENCE ENGINE CANDIDATE VALIDATION

AIW: CAE  
STATUS: APPROVED ACI EXECUTED ON FEATURE BRANCH — NOT MERGED — OPERATOR / JAY REVIEW REQUIRED

Permanent copy of the Operator ACI (APPROVED FOR EXECUTION). This execution evaluates one commercially acceptable Audio Intelligence candidate on the locked Jay Garrett master. It does not create a Song Intelligence Record and does not reopen other Song Intelligence engines.

## Mission

Determine whether a commercially acceptable local audio-analysis engine can derive useful Audio Intelligence directly from the finished Jay Garrett master.

Authorized capability only:

FINISHED MASTER WAV → AUDIO INTELLIGENCE ANALYSIS → STRUCTURED AUDIO CHARACTERISTICS

## Constraints honored

- New branch `feature/aci-a2l-si-007-audio-intelligence` from SI-006 `feature/aci-a2l-si-006-lyric-intelligence` @ `e5efb38`.
- Implementation commit recorded after commit.
- Locked master SHA-256 `bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be` unchanged. Source audio was not remastered, normalized, or overwritten.
- Selected candidate: Hugging Face `transformers` `ClapModel` with `laion/larger_clap_music` revision `a0b4534a14f58e20944452dff00a22a06ce629d1`.
- License: Apache-2.0 (commercially acceptable). Runtime gate refuses non-commercial licenses.
- Isolated sidecar `.venv-clap` (Python 3.12.10, transformers 4.44.2). Not installed into Python 3.14 A2L.
- CPU only. GPU not required. No cloud inference.
- Bounded ACI vocabularies with documented prompt templates. Rankings are cosine similarity, not calibrated probabilities. Labels were not tuned after seeing audio.
- Energy uses RMS and onset density (MEASURED); interpretive HIGH/MEDIUM/LOW ENERGY is MACHINE-DERIVED. Not mastering/QC.
- Incomplete SI-005 snapshot weights were discarded. A complete local blob matching Hugging Face `X-Linked-Size` / ETag was reused; no CLAP restart of the prior killed curl.
- Results are MACHINE-DERIVED / MEASURED as applicable. Not written into approved lyrics or release authority.
- Rhythm/Structure, Key/Mode, and Lyric Intelligence were not reopened.
- Not merged. Not pushed. Song Intelligence Record not created.

## Engine #3 prior deferral

Previous acquisition was stopped solely for network constraint (not a technical failure): ~740 MB target, ~139 MB / ~18% at ~245 KB/s, ~10 minutes, terminated. This ACI authorized continuation on a better connection and reuse of a valid complete cache object.

## Explicitly out of scope

Song Intelligence Record, SI UI, chords, mastering/QC, source-separation product path, EPK, marketing copy, radio targeting, distributor integration, lyric mutation/retranscription, reopen of engines #1/#2/#4.
