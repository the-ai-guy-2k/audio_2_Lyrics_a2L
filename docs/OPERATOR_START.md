# A2L operator application start (ACI-A2L-015)

The operator application is a local stdlib web app. It is not a hosted product.

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

The default Python 3.11+ interpreter can start the application after `pip install -e ".[dev]"`:

```bash
python -m a2l app
```

Same URL: http://127.0.0.1:8780/

That interpreter on this workstation is Python 3.14.3 and does **not** include faster-whisper. Upload and review UI load. Extract with FASTER-WHISPER returns: "That transcription engine is not available in this environment."

## Alternate engine (NVIDIA Parakeet)

Do not promote Parakeet. It is optional.

```bash
.venv-parakeet\Scripts\python.exe -m a2l app
```

Still http://127.0.0.1:8780/ unless `--port` is changed. Isolated setup: [requirements-nvidia-parakeet.txt](../requirements-nvidia-parakeet.txt). Python 3.12, nemo-toolkit 3.0.0, local checkpoint `%USERPROFILE%\.cache\a2l-parakeet\parakeet-tdt-0.6b-v2.nemo`. This workstation previously needed several GB of memory; Parakeet is not the default.

## What the operator does not need

Python internals, artifact directories, SHA paths, model files, Nebula ACI folders, or candidate directories are not required to use the application screens.
