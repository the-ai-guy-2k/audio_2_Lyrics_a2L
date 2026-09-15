# A2L operator application start

The operator application is the **product-facing** path. It is a local stdlib web app, not a hosted product.

**Operator application:** http://127.0.0.1:8780/  
**Engineering review interface:** http://127.0.0.1:8765/ (`python -m a2l review`) — not the product path.

## Engines

| Role | Engine |
| --- | --- |
| **PRIMARY** | faster-whisper / Whisper large-v3 |
| **ALTERNATE** | NVIDIA Parakeet / TDT-0.6B-V2 (optional; not promoted) |

## Supported start (primary extract)

Real lyric extraction with the primary engine needs the isolated faster-whisper environment (Python 3.12). On this workstation:

```bash
.venv-faster-whisper\Scripts\python.exe -m a2l app
```

Open http://127.0.0.1:8780/

Create that environment once:

```bash
py -3.12 -m venv .venv-faster-whisper
.venv-faster-whisper\Scripts\python.exe -m pip install -e ".[dev,transcribe]"
```

Pinned packages: [requirements-faster-whisper.txt](../requirements-faster-whisper.txt). The venv is gitignored.

## UI-only / tests

The default Python 3.11+ interpreter can start the **UI** after `pip install -e ".[dev]"`:

```bash
python -m a2l app
```

Same URL: http://127.0.0.1:8780/

That interpreter on this workstation is Python 3.14.3 and does **not** include faster-whisper. Upload and review UI load. Extract with FASTER-WHISPER returns: "That transcription engine is not available in this environment." Do not treat default Python 3.14 as capable of faster-whisper extraction.

Song Intelligence is on the same operator URL. Full Song Intelligence is the default. Heavyweight analyzers run sequentially in their isolated environments (`.venv-key-mode`, `.venv-clap`, `.venv-all-in-one`) when the UI interpreter cannot import them. GPU and cloud are not required.

## Alternate engine (NVIDIA Parakeet)

Parakeet is alternate. It is not the primary engine and is not promoted.

```bash
.venv-parakeet\Scripts\python.exe -m a2l app
```

Still http://127.0.0.1:8780/ unless `--port` is changed. Isolated setup: [requirements-nvidia-parakeet.txt](../requirements-nvidia-parakeet.txt). Python 3.12, nemo-toolkit 3.0.0, local checkpoint `%USERPROFILE%\.cache\a2l-parakeet\parakeet-tdt-0.6b-v2.nemo`. This workstation previously needed several GB of memory; Parakeet is not the default.

## Engineering review interface

```bash
python -m a2l review
```

Open http://127.0.0.1:8765/

This page is for engineering review of the primary pipeline draft. It is not the operator application. Title/artist intake lives on the operator app at :8780.

## What the operator does not need

Python internals, artifact directories, SHA paths, model files, Nebula ACI folders, or candidate directories are not required to use the application screens.
