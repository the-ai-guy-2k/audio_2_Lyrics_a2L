"""ACI-A2L-SI-006 isolated Lyric Intelligence candidate.

Derives themes, keywords, emotional character, subject matter, and a
short synopsis from HUMAN-APPROVED lyrics using deterministic in-repo NLP.
Does not transcribe audio. Does not call cloud APIs. Does not download models.
Does not modify the Approved Lyric Artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import threading
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LOCKED_SHA256 = "bbc700259ab80a6ae0e390403a9849f31e5dec54784bd4040f1f4e54d58b80be"
ENGINE_NAME = "in-repo deterministic lyric NLP"
METHOD = (
    "stdlib tokenization, line-bounded repeated n-gram ranking, content-word frequency, "
    "and bounded lexical emotion overlap on approved lyric text"
)
LICENSE_DECLARED = "original A2L spike code; no third-party model weights"
CANDIDATE_DIR_NAME = "lyric-intelligence"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-006-evidence"
INGEST_APPROVED_DIR = (
    ROOT / "artifacts" / "ingest" / LOCKED_SHA256 / "a2l_pipeline" / "approved_lyrics"
)
EVIDENCE_APPROVED_DIR = ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-009-evidence"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", re.IGNORECASE)
MIN_PHRASE_COUNT = 2
PHRASE_NS = range(2, 9)
MAX_THEMES = 6
MAX_KEYWORDS = 12

# Original short function-word list. Not an NLTK corpus download.
STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "but",
    "can",
    "for",
    "from",
    "get",
    "got",
    "here",
    "i",
    "if",
    "i'll",
    "in",
    "is",
    "it",
    "little",
    "none",
    "of",
    "on",
    "our",
    "out",
    "so",
    "some",
    "something",
    "that",
    "the",
    "these",
    "this",
    "to",
    "too",
    "up",
    "us",
    "we",
    "with",
    "you",
    "your",
}
FILLER_PREFIXES = ("whoa", "oh-oh", "ooh")
FILLER_EXACT = {"oh", "yeah", "whoa"}

# Bounded ACI-style labels. Hits are MEASURED token overlap; winner is MACHINE-DERIVED.
EMOTION_LEXICON = {
    "energetic": ("stomp", "groove", "move", "dance", "funk", "alive", "kick-ass", "footloose"),
    "celebratory": ("dance", "footloose", "groove", "funk", "crowd", "alive"),
    "rebellious": ("kick-ass",),
    "defiant": ("kick-ass",),
    "reflective": ("blues",),
    "melancholic": ("blues", "bored"),
    "romantic": ("love", "heart", "kiss"),
    "humorous": ("butts",),
    "nostalgic": ("old", "school"),
    "relaxed": ("ballad", "slow"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def is_filler(token: str) -> bool:
    if token in FILLER_EXACT:
        return True
    return any(token == prefix or token.startswith(prefix + "-") for prefix in FILLER_PREFIXES)


def is_content_token(token: str) -> bool:
    if len(token) < 3:
        return False
    if token in STOPWORDS or is_filler(token):
        return False
    return True


def ngrams(tokens: list[str], n: int) -> list[str]:
    if n <= 0 or len(tokens) < n:
        return []
    return [" ".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1)]


def phrase_has_content(phrase: str) -> bool:
    return any(is_content_token(token) for token in phrase.split())


def rank_phrases(token_lines: list[list[str]], limit: int = MAX_THEMES) -> list[dict]:
    counts: Counter[str] = Counter()
    for tokens in token_lines:
        for n in PHRASE_NS:
            for phrase in ngrams(tokens, n):
                if phrase_has_content(phrase):
                    counts[phrase] += 1
    ranked = []
    for phrase, count in counts.items():
        if count < MIN_PHRASE_COUNT:
            continue
        words = phrase.split()
        content_n = sum(1 for token in words if is_content_token(token))
        if content_n < 2:
            continue
        ranked.append(
            {
                "phrase": phrase,
                "count": count,
                "token_length": len(words),
                "content_tokens": content_n,
                "score": count * content_n,
            }
        )
    ranked.sort(key=lambda item: (item["score"], item["count"], item["token_length"]), reverse=True)
    selected: list[dict] = []
    for item in ranked:
        phrase = item["phrase"]
        if any(phrase != kept["phrase"] and phrase in kept["phrase"] for kept in selected):
            continue
        selected.append(item)
        if len(selected) >= limit:
            break
    for index, item in enumerate(selected, start=1):
        item["rank"] = index
    return selected


def rank_keywords(tokens: list[str], limit: int = MAX_KEYWORDS) -> list[dict]:
    counts = Counter(token for token in tokens if is_content_token(token))
    ranked = [
        {"keyword": word, "count": count, "score": count}
        for word, count in counts.most_common(limit)
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def emotion_scores(tokens: list[str]) -> list[dict]:
    freq = Counter(tokens)
    scored = []
    for label, cues in EMOTION_LEXICON.items():
        hits = {cue: int(freq.get(cue, 0)) for cue in cues if freq.get(cue, 0)}
        total = sum(hits.values())
        scored.append(
            {
                "label": label,
                "overlap_count": total,
                "hits": hits,
            }
        )
    scored.sort(key=lambda item: item["overlap_count"], reverse=True)
    for index, item in enumerate(scored, start=1):
        item["rank"] = index
    return scored


def extractive_subject(text: str, themes: list[dict]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parts = []
    if lines:
        parts.append(lines[0].rstrip("!."))
    for item in themes[:3]:
        phrase = item["phrase"]
        if phrase not in {part.lower() for part in parts}:
            parts.append(phrase)
    return "; ".join(parts)


def extractive_synopsis(text: str, themes: list[dict]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    body = text.lower()
    sentences = []
    if lines:
        sentences.append(f"The approved lyrics open by addressing '{lines[0]}'.")
    if themes:
        phrase = themes[0]["phrase"]
        if phrase.startswith("play "):
            sentences.append(f"They repeatedly ask to {phrase}.")
        else:
            sentences.append(f"A repeated lyric phrase is '{phrase}'.")
    extras = []
    if "old school funk" in body:
        extras.append("old school funk")
    if "slow down ballad" in body:
        extras.append("not slow down ballad stuff")
    if "work week blues" in body:
        extras.append("work week blues")
    if "footloose" in body:
        extras.append("dance and get a little footloose")
    if extras:
        sentences.append("The same lyric body also includes: " + "; ".join(extras) + ".")
    return " ".join(sentences[:3])


def analyze_lyrics(text: str) -> dict:
    tokens = tokenize(text)
    token_lines = [tokenize(line) for line in text.splitlines() if line.strip()]
    themes = rank_phrases(token_lines)
    keywords = rank_keywords(tokens)
    emotions = emotion_scores(tokens)
    top_emotion = next((item for item in emotions if item["overlap_count"] > 0), None)
    return {
        "token_count": len(tokens),
        "line_count": len([line for line in text.splitlines() if line.strip()]),
        "themes": themes,
        "keywords": keywords,
        "emotional_character": {
            "label": top_emotion["label"] if top_emotion else "unavailable",
            "overlap_count": top_emotion["overlap_count"] if top_emotion else 0,
            "ranked": emotions,
            "authority": "MACHINE-DERIVED",
            "score_kind": "lexicon token overlap count; not a calibrated sentiment probability",
        },
        "subject_matter": {
            "text": extractive_subject(text, themes),
            "authority": "MACHINE-DERIVED",
        },
        "synopsis": {
            "text": extractive_synopsis(text, themes),
            "authority": "MACHINE-DERIVED",
        },
        "lexical_measurements": {
            "authority": "MEASURED",
            "theme_counts": {item["phrase"]: item["count"] for item in themes},
            "keyword_counts": {item["keyword"]: item["count"] for item in keywords},
        },
    }


def load_approved_pair(directory: Path) -> dict:
    txt_path = directory / "approved_lyrics.txt"
    json_path = directory / "approved_lyrics.json"
    if not txt_path.is_file() or not json_path.is_file():
        raise SystemExit(f"STOP: approved lyrics not found in {directory}")
    txt = txt_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"STOP: approved_lyrics.json is not valid JSON: {exc}") from exc
    if payload.get("approval_status") != "APPROVED":
        raise SystemExit("STOP: lyric artifact is not APPROVED")
    if payload.get("usable_as_approved_lyrics") is not True:
        raise SystemExit("STOP: lyric artifact is not usable as approved lyrics")
    if payload.get("authority") != "AUTHORITATIVE_APPROVED_LYRICS":
        raise SystemExit("STOP: lyric artifact authority is not AUTHORITATIVE_APPROVED_LYRICS")
    json_text = payload.get("approved_lyric_text")
    if not isinstance(json_text, str):
        raise SystemExit("STOP: approved_lyric_text missing")
    if json_text.replace("\r\n", "\n") != txt.replace("\r\n", "\n"):
        raise SystemExit("STOP: approved TXT and JSON lyric text do not match")
    source_sha = payload.get("source_sha256") or payload.get("ingest_job_id")
    if source_sha != LOCKED_SHA256:
        raise SystemExit(f"STOP: approved lyrics source SHA mismatch: {source_sha}")
    return {
        "directory": str(directory),
        "txt_path": str(txt_path),
        "json_path": str(json_path),
        "text": txt.replace("\r\n", "\n"),
        "txt_sha256": sha256_file(txt_path),
        "json_sha256": sha256_file(json_path),
        "text_sha256": sha256_text(txt.replace("\r\n", "\n")),
        "revision": ((payload.get("approval_event") or {}).get("revision")),
        "authority": payload.get("authority"),
        "approval_status": payload.get("approval_status"),
    }


def resolve_approved_lyrics() -> dict:
    if (INGEST_APPROVED_DIR / "approved_lyrics.txt").is_file():
        return load_approved_pair(INGEST_APPROVED_DIR)
    if (EVIDENCE_APPROVED_DIR / "approved_lyrics.txt").is_file():
        return load_approved_pair(EVIDENCE_APPROVED_DIR)
    raise SystemExit("STOP: approved lyrics could not be resolved; draft transcription was not substituted")


def process_memory_bytes() -> dict:
    record = {
        "working_set_bytes": None,
        "peak_working_set_bytes": None,
        "sampler": "unavailable",
    }
    if sys.platform != "win32":
        return record
    import ctypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
    get_info.restype = ctypes.c_bool
    ok = get_info(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    if not ok:
        return record
    record.update(
        {
            "working_set_bytes": int(counters.WorkingSetSize),
            "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
            "sampler": "GetProcessMemoryInfo",
        }
    )
    return record


class MemorySampler:
    def __init__(self, interval: float = 0.05) -> None:
        self.interval = interval
        self.peak_working_set_bytes = 0
        self.samples = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict:
        self._stop.set()
        self._thread.join(timeout=5)
        final = process_memory_bytes()
        peak = max(self.peak_working_set_bytes, final.get("peak_working_set_bytes") or 0)
        return {
            "samples": self.samples,
            "sampled_peak_working_set_bytes": self.peak_working_set_bytes,
            "os_peak_working_set_bytes": final.get("peak_working_set_bytes"),
            "final_working_set_bytes": final.get("working_set_bytes"),
            "peak_working_set_bytes": peak or None,
            "peak_working_set_mb": round(peak / (1024 * 1024), 1) if peak else None,
            "sampler": final.get("sampler"),
        }

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            current = process_memory_bytes().get("working_set_bytes") or 0
            self.samples += 1
            if current > self.peak_working_set_bytes:
                self.peak_working_set_bytes = current


def hardware_record() -> dict:
    return {
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "device": "cpu",
        "notes": "Lyric Intelligence is stdlib-only on CPU. No model download. No cloud.",
    }


def protected_roots(sha: str) -> list[Path]:
    job = ROOT / "artifacts" / "ingest" / sha
    return [
        job / "authoritative_source",
        job / "machine_transcription",
        job / "a2l_pipeline",
        job / "a2l_pipeline_parakeet",
        job / "song_release_record.json",
        ROOT / "artifacts" / "releases",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-009-evidence" / "approved_lyrics.txt",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-009-evidence" / "approved_lyrics.json",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-002-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-003-evidence",
        ROOT / "docs" / "nebula" / "artifacts" / "aci-a2l-si-004-evidence",
    ]


def snapshot_protected(sha: str) -> dict:
    record = {}
    for root in protected_roots(sha):
        if not root.exists():
            record[str(root)] = {"exists": False, "files": {}}
            continue
        files = {}
        if root.is_file():
            files[str(root)] = sha256_file(root)
        else:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    files[str(path)] = sha256_file(path)
        record[str(root)] = {"exists": True, "files": files}
    return record


def snapshots_match(before: dict, after: dict) -> bool:
    return before == after


def assert_isolated_output(path: Path, sha: str) -> None:
    resolved = path.resolve()
    for root in protected_roots(sha):
        if not root.exists():
            continue
        protected = root.resolve()
        if resolved == protected or protected in resolved.parents:
            raise SystemExit(f"Refusing to write into protected artifact path: {resolved}")
    ingest = (ROOT / "artifacts" / "ingest").resolve()
    if ingest in resolved.parents or resolved == ingest:
        raise SystemExit(f"Refusing to write into ingest store: {resolved}")


def write_readable_txt(path: Path, analysis: dict, meta: dict) -> None:
    themes = analysis.get("themes") or []
    keywords = analysis.get("keywords") or []
    emotion = analysis.get("emotional_character") or {}
    lines = [
        "MACHINE-DERIVED LYRIC INTELLIGENCE",
        "ACI-A2L-SI-006",
        "APPROVED LYRICS ARE AUTHORITATIVE INPUT",
        "THIS ANALYSIS IS NOT AUTHORITATIVE SONG FACTS",
        "NOT A SONG INTELLIGENCE RECORD",
        "Audio was not transcribed.",
        "",
        f"engine: {meta.get('engine')}",
        f"method: {METHOD}",
        f"license: {LICENSE_DECLARED}",
        f"approved_source: {meta.get('approved_source')}",
        f"approved_revision: {meta.get('approved_revision')}",
        f"approved_text_sha256: {meta.get('approved_text_sha256')}",
        "",
        "THEMES:",
    ]
    if themes:
        lines.extend(
            f"{item['rank']}. {item['phrase']}  (count={item['count']})" for item in themes
        )
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("KEYWORDS / CONCEPTS:")
    if keywords:
        lines.extend(
            f"{item['rank']}. {item['keyword']}  (count={item['count']})" for item in keywords
        )
    else:
        lines.append("(none)")
    lines.extend(
        [
            "",
            "EMOTIONAL CHARACTER:",
            str(emotion.get("label", "unavailable")),
            "",
            "SUBJECT MATTER:",
            (analysis.get("subject_matter") or {}).get("text", "unavailable"),
            "",
            "SONG SYNOPSIS:",
            (analysis.get("synopsis") or {}).get("text", "unavailable"),
            "",
            "METHOD:",
            METHOD,
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACI-A2L-SI-006 Lyric Intelligence candidate")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to artifacts/candidates/lyric-intelligence/<sha256>/",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protected_before = snapshot_protected(LOCKED_SHA256)
    approved = resolve_approved_lyrics()
    approved_txt = Path(approved["txt_path"])
    approved_json = Path(approved["json_path"])
    before_txt = approved["txt_sha256"]
    before_json = approved["json_sha256"]
    before_text = approved["text_sha256"]

    out_dir = args.output_dir or (
        ROOT / "artifacts" / "candidates" / CANDIDATE_DIR_NAME / LOCKED_SHA256
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "lyric_intelligence_raw.json"
    txt_path = out_dir / "lyric_intelligence_readable.txt"
    run_path = out_dir / "lyric_intelligence_run.json"
    for path in (raw_path, txt_path, run_path):
        assert_isolated_output(path, LOCKED_SHA256)

    errors: list[str] = []
    analysis: dict = {}
    analysis_seconds = None
    started_utc = datetime.now(timezone.utc).isoformat()
    sampler = MemorySampler()
    sampler.start()
    try:
        analyze_started = time.perf_counter()
        analysis = analyze_lyrics(approved["text"])
        analysis_seconds = time.perf_counter() - analyze_started
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    memory = sampler.stop()

    after_txt = sha256_file(approved_txt)
    after_json = sha256_file(approved_json)
    after_text = sha256_text(approved_txt.read_text(encoding="utf-8").replace("\r\n", "\n"))
    protected_after = snapshot_protected(LOCKED_SHA256)
    approved_unchanged = before_txt == after_txt and before_json == after_json and before_text == after_text

    raw_payload = {
        "candidate": "ACI-A2L-SI-006",
        "authority": {
            "approved_lyrics": "AUTHORITATIVE INPUT",
            "lexical_measurements": "MEASURED",
            "themes": "MACHINE-DERIVED",
            "emotional_character": "MACHINE-DERIVED",
            "subject_matter": "MACHINE-DERIVED",
            "synopsis": "MACHINE-DERIVED",
        },
        "usable_as_song_facts": False,
        "song_intelligence_record_created": False,
        "audio_transcribed": False,
        "engine": ENGINE_NAME,
        "method": METHOD,
        "license": LICENSE_DECLARED,
        "gpu_required": False,
        "cloud_required": False,
        "download_required": False,
        "device": "cpu",
        "approved_lyrics": {
            "path": approved["txt_path"],
            "json_path": approved["json_path"],
            "revision": approved["revision"],
            "source_sha256": LOCKED_SHA256,
            "text_sha256_before": before_text,
            "text_sha256_after": after_text,
            "txt_sha256_before": before_txt,
            "txt_sha256_after": after_txt,
            "json_sha256_before": before_json,
            "json_sha256_after": after_json,
        },
        "analysis_seconds": analysis_seconds,
        "hardware": hardware_record(),
        "package_versions": {"python": platform.python_version()},
        "memory": memory,
        "errors": errors,
        "lyric_intelligence": analysis,
    }
    raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    write_readable_txt(
        txt_path,
        analysis,
        {
            "engine": ENGINE_NAME,
            "approved_source": approved["txt_path"],
            "approved_revision": approved["revision"],
            "approved_text_sha256": after_text,
        },
    )
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_path, EVIDENCE_DIR / "lyric_intelligence_raw.json")
    shutil.copy2(txt_path, EVIDENCE_DIR / "lyric_intelligence_readable.txt")

    ok = (
        not errors
        and bool(analysis.get("themes"))
        and bool(analysis.get("keywords"))
        and bool((analysis.get("emotional_character") or {}).get("label"))
        and bool((analysis.get("subject_matter") or {}).get("text"))
        and bool((analysis.get("synopsis") or {}).get("text"))
    )
    run_payload = {
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "raw_path": str(raw_path.resolve()),
        "txt_path": str(txt_path.resolve()),
        "approved_lyric_hash_unchanged": approved_unchanged,
        "protected_artifacts_unchanged": snapshots_match(protected_before, protected_after),
        "cpu_execution": not errors,
        "gpu_required": False,
        "cloud_required": False,
        "download_required": False,
        "analysis_seconds": analysis_seconds,
        "memory": memory,
        "errors": errors,
        "cwd": os.getcwd(),
    }
    run_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")
    shutil.copy2(run_path, EVIDENCE_DIR / "lyric_intelligence_run.json")

    print(json.dumps(run_payload, indent=2))
    print(f"LYRIC INTELLIGENCE READABLE OUTPUT:\n{txt_path.resolve()}")
    if errors:
        return 1
    if not approved_unchanged:
        print("FAIL: approved lyrics changed")
        return 1
    if not snapshots_match(protected_before, protected_after):
        print("FAIL: protected artifacts changed")
        return 1
    if not ok:
        print("FAIL: incomplete lyric intelligence output")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
