"""In-process worker for Song Intelligence venv fallback.

Invoked as: python -m a2l.song_intelligence_worker
Does not use venv recursion. Reads one JSON object from stdin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    engine_id = payload.get("engine_id")
    song = payload.get("song") or {}
    for key in ("working_path", "source_path", "ui_dir", "job_dir"):
        if song.get(key):
            song[key] = Path(song[key])
    from a2l.song_intelligence_engines import default_runners

    runner = default_runners(allow_venv=False).get(engine_id)
    if runner is None:
        json.dump({"status": "Failed", "message": "Unknown engine.", "fields": []}, sys.stdout)
        return 1
    result = runner(song)
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
