# ACI-A2L-011 evidence

Isolated NVIDIA Parakeet TDT 0.6B v2 candidate. Does **not** replace the primary faster-whisper / Whisper large-v3 path.

- `nvidia_parakeet_lyrics.txt` — human-readable machine transcription for Operator inspection
- `nvidia_parakeet_raw.json` — versions, hardware, hypothesis, actual text
- `nvidia_parakeet_run.json` — SHA verification and protected-artifact checks

Runtime copies also exist under `artifacts/candidates/nvidia-parakeet/<sha256>/` (gitignored).

Full song completed on CPU. Model load 18.11 s. Transcription 78.78 s. Source SHA unchanged. Primary pipeline artifacts unchanged.
