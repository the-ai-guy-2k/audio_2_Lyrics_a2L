# A2L current architecture (implemented)

**Authority:** ACI-A2L-SI-PROM-002 promotion of the validated Song Intelligence product UI (ACI-A2L-SI-011) to `deployable`. Product-facing operator path remains http://127.0.0.1:8780/.

## Implemented flow

```text
Operator application (python -m a2l app)  ← product-facing, http://127.0.0.1:8780/
  Upload WAV + optional song title / artist (filename is not the title)
    → choose engine BEFORE transcription
      PRIMARY: faster-whisper / Whisper large-v3  → ingest_job/a2l_pipeline/
      ALTERNATE: NVIDIA Parakeet / TDT-0.6B-V2   → ingest_job/a2l_pipeline_parakeet/
  → ingest (CONTROL A)
  → persist operator metadata at ingest_job/song_metadata.json
  → transcribe (selected engine; whisper-1 baseline preserved)
  → uncertainty (flag, do not invent)
  → lyric structuring (timed annotated draft, do not rewrite)
  → human review (paragraph lyrics, optional title/artist correction, save does not approve)
  → explicit human approval (confirm=true)
  → canonical approved_lyrics.txt / approved_lyrics.json (title/artist retained if supplied)
  → derived Output presentations (default: STANDARD LYRIC SHEET uses supplied metadata)
  → user download filename from supplied Artist / Song Title (sanitized; does not rename canonical files)
  → song release record (credits/rights/ISRC if entered; missing stays MISSING; not distribution)
  → album release manifest (Operator album identity + ordered song membership; live song-record truth)
  → album release readiness (A2L INTERNAL READY/INCOMPLETE from current manifest + song records; not distributor readiness)
  → release package export (derived ZIP of current governed album/song artifacts; master audio referenced, not copied; not a distributor package)
  → Song Intelligence (select governed song → Full Song Intelligence default → Analyze song → derived UI results with provenance; not a governed SI Record)
  → optional reopen (archives prior approval + derived exports) → metadata may be corrected → reapprove
```

Primary supported start: `.venv-faster-whisper\Scripts\python.exe -m a2l app`  
See [OPERATOR_START.md](../../OPERATOR_START.md).

The engineering review page remains `python -m a2l review` at http://127.0.0.1:8765/ and is **not** the product-facing path.

Fixed test song: [FIXED_TEST_SONG.md](../FIXED_TEST_SONG.md)

No verse/chorus labels are invented. Vocal isolation is not in the pipeline. Song title and artist are operator-supplied and optional; the WAV filename is not used as a title. After approval the operator Output screen shows a Standard Lyric Sheet derived from the approved artifact; canonical TXT/JSON remain authoritative. Downloaded files are named from that metadata when present. The Album screen organizes existing Song Release Records. Release Readiness reports A2L INTERNAL READY/INCOMPLETE from current governed records; it is not distributor or commercial readiness. Album **Export release package** writes a derived ZIP of that current truth; it does not copy master audio or invent missing release data. The locked Jay song's **faster-whisper** approved lyrics (ACI-A2L-009 Amendment 01, revision 2) were not modified. Parakeet output is a separate unapproved chain. Song Intelligence is available in the operator application (ACI-A2L-SI-011) as a product UI that orchestrates the promoted analyzers. The on-screen aggregation is derived and non-authoritative. There is **no** governed Song Intelligence Record and no Song Intelligence approval action. Rhythm + Structure is an ENGINEERING WIN (All-In-One / Harmonix; SI-003 HTDemucs is diagnostic plumbing only, not an A2L source-separation product). Key + Mode is an ENGINEERING WIN (librosa chroma_cqt + Krumhansl–Schmuckler); MUSICAL VALIDATION pending Jay. Audio Intelligence is PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD: Energy / Intensity WIN (CLAP + RMS/onset), Acoustic / Electronic WIN (CLAP), Genre / Style WIN (AST), Vocal PARTIAL (CLAP), Instrumentation PARTIAL (PANNs; not WIN). The instrumentation defect remains open in the bug-fix lane (`docs/nebula/defects/DEF-A2L-SI-INSTRUMENTATION.md`) and must not block continued Song Intelligence development. Lyric Intelligence is an ENGINEERING WIN (deterministic NLP on AUTHORITATIVE approved lyrics); SEMANTIC VALIDATION pending Jay. Machine-derived SI outputs are not human-approved or authoritative by promotion.
