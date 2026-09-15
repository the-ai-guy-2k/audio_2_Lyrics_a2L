# DEF-A2L-SI-INSTRUMENTATION

**Title:** INSTRUMENTATION INTELLIGENCE UNRESOLVED  
**Opened by:** ACI-A2L-SI-010 (Repair Attempt 3 of 3, FINAL)  
**Disposition:** DEFER TO BUG-FIX LANE  
**Must not block:** continued Song Intelligence development  
**No fourth repair ACI.**  
**Promotion:** Preserved unchanged by ACI-A2L-SI-PROM-001, ACI-A2L-SI-PROM-002, and ACI-A2L-SI-PROM-003. Not closed. Not marked WIN.

## Current engineering truth

Engine #3 Audio Intelligence is **PARTIAL PASS — ACCEPTED FOR CONTINUED BUILD**.

| Category | Status | Source |
| --- | --- | --- |
| Energy / Intensity | WIN | SI-007 CLAP + RMS/onset |
| Acoustic / Electronic | WIN | SI-008 CLAP CONTROL |
| Genre / Style | WIN | SI-009 AST |
| Vocal Characteristics | PARTIAL | SI-008 CLAP ensemble |
| Instrumentation | PARTIAL after SI-010; still not an Engineering WIN | SI-007 CLAP NO WIN → SI-008 NO WIN → SI-009 AST NO WIN → SI-010 PANNs PARTIAL |

## What SI-010 showed (do not retune after the fact)

PANNs Cnn14 on the locked Jay master, native AudioSet instrument subset, clipwise_mean over 21 × 10s chunks:

- Guitar mean=0.1705 max=0.7221
- Plucked string instrument mean=0.1311 max=0.6417
- Electric guitar mean=0.0433 max=0.3206
- Drum kit mean=0.0190 max=0.0378
- Synthesizer mean=0.0006

Precommitted PANNs operating point 0.50 produced strong_count=0. Result PARTIAL (mean ≥ 0.10 and spread ≥ 0.10), not WIN. AST 0.15 was not lowered.

## Bug-fix lane notes

Later work may evaluate other instrument-presence approaches. It must not be framed as SI-011 / Repair Attempt 4 of the SI-007–010 series. Musical verification of which instruments were actually played remains PENDING JAY.
