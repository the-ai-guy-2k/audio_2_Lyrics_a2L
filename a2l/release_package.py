"""ACI-A2L-REL-004 release package export.

Builds a portable A2L release-preparation ZIP from current governed album
truth. Missing business, legal, identifier, and lyric data is preserved,
not invented. The ZIP is a derived artifact, not a new metadata authority.
Master WAV files are referenced, not copied.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from a2l.album_manifest import (
    RELEASE_TYPES,
    default_manifest_path,
    detect_pipeline_dirname,
    load_album_manifest,
)
from a2l.album_readiness import (
    READINESS_NOTE,
    assess_album_readiness,
    default_readiness_path,
)
from a2l.approve import default_approved_json_path, default_approved_txt_path
from a2l.errors import ExportError, ReleaseError
from a2l.export import (
    INTERNAL_ARTIFACT_NAMES,
    SUPPORTED_FORMATS,
    default_exports_dir,
    format_approved_export,
    sanitize_filename_component,
)
from a2l.ingest import MANIFEST_FILENAME, SOURCE_FILENAME
from a2l.pipeline import ROOT
from a2l.release_record import (
    INCOMPLETE,
    READY,
    RECORD_FILENAME,
    STATUS_AVAILABLE,
    load_or_create_release_record,
)

SCHEMA_VERSION = "1.0.0"
PACKAGE_VERSION = "1.0.0"
PRODUCER_ACI = "ACI-A2L-REL-004"
PACKAGE_TYPE = "A2L_RELEASE_PREPARATION_PACKAGE"
AUTHORITY = "DERIVED_RELEASE_PACKAGE_EXPORT"
EXPORTS_DIRNAME = "exports"
PACKAGE_MANIFEST_NAME = "package_manifest.json"
RELEASE_SUMMARY_NAME = "release_summary.txt"
SOURCE_REFERENCES_NAME = "source_references.json"
FALLBACK_ZIP_NAME = "A2L_Release_Package.zip"
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}
_MAX_STEM_CHARS = 180
DISCLAIMER = (
    "This package is an A2L release-preparation export for operator review, "
    "handoff, and archive. It is not proof of distributor acceptance, store "
    "delivery, legal registration, or commercial release."
)


def default_package_exports_root(release_id: str, artifact_root: str | Path | None = None) -> Path:
    return default_manifest_path(release_id, artifact_root).parent / EXPORTS_DIRNAME


def package_download_name(album_title, primary_artist, release_id: str) -> str:
    """Filesystem-safe ZIP name from governed identity. Does not invent title or artist."""
    artist = _underscore_component(primary_artist)
    title = _underscore_component(album_title)
    if artist and title:
        stem = f"{artist}_{title}_A2L_Release_Package"
    elif title:
        stem = f"{title}_A2L_Release_Package"
    elif artist:
        stem = f"{artist}_A2L_Release_Package"
    else:
        ident = "".join(ch for ch in str(release_id or "") if ch.isalnum()) or "album"
        stem = f"{ident}_A2L_Release_Package"
    return _finalize_zip_name(stem)


def package_content_disposition(filename: str) -> str:
    name = _finalize_zip_name(filename)
    encoded = quote(name, safe="")
    try:
        name.encode("ascii")
        ascii_name = name.replace("\\", "_").replace('"', "")
        return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
    except UnicodeEncodeError:
        return f"attachment; filename=\"{FALLBACK_ZIP_NAME}\"; filename*=UTF-8''{encoded}"


def export_release_package(
    release_id: str,
    artifact_root: str | Path | None = None,
    now: str | None = None,
) -> dict:
    """Reassess current album truth and write a derived ZIP under exports/."""
    album = load_album_manifest(release_id, artifact_root=artifact_root, now=now)
    stamp = now or datetime.now(timezone.utc).isoformat()
    readiness = assess_album_readiness(album["release_id"], artifact_root=artifact_root, now=stamp, persist=True)
    download_name = package_download_name(album.get("album_title"), album.get("primary_artist"), album["release_id"])
    files, completeness, provenance = _package_files(album, readiness, artifact_root, stamp)
    included = sorted(files)
    manifest = _package_manifest(album, readiness, stamp, download_name, included, completeness, provenance)
    files[PACKAGE_MANIFEST_NAME] = _json_bytes(manifest)
    files[f"provenance/{SOURCE_REFERENCES_NAME}"] = _json_bytes(provenance)
    files[RELEASE_SUMMARY_NAME] = _summary_text(album, readiness, completeness, stamp).encode("utf-8")
    included = sorted(files)
    manifest["included_files"] = included
    files[PACKAGE_MANIFEST_NAME] = _json_bytes(manifest)

    export_dir = default_package_exports_root(album["release_id"], artifact_root) / _export_folder_name(stamp)
    export_dir.mkdir(parents=True, exist_ok=True)
    zip_path = export_dir / download_name
    _write_zip(zip_path, files, stamp)
    sidecar = export_dir / PACKAGE_MANIFEST_NAME
    sidecar.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    relative = _posix_relative(_artifact_root(artifact_root), zip_path)
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "package_type": PACKAGE_TYPE,
        "package_version": PACKAGE_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_package": False,
        "master_audio_included": False,
        "release_id": album["release_id"],
        "album_title": album.get("album_title"),
        "primary_artist": album.get("primary_artist"),
        "release_type": album.get("release_type"),
        "overall_state": readiness["overall_state"],
        "readiness_note": READINESS_NOTE,
        "generated_at": stamp,
        "download_name": download_name,
        "relative_export_path": relative,
        "included_files": included,
        "missing_album_fields": readiness.get("missing_album_fields") or [],
        "tracks": readiness.get("tracks") or [],
        "summary": readiness.get("summary") or {},
        "completeness": completeness,
        "zip_path": zip_path,
    }


def public_package_payload(result: dict) -> dict:
    return {
        "ok": True,
        "package_type": result["package_type"],
        "package_version": result["package_version"],
        "authority": result["authority"],
        "produced_by": result["produced_by"],
        "release_id": result["release_id"],
        "album_title": result["album_title"],
        "primary_artist": result["primary_artist"],
        "release_type": result["release_type"],
        "overall_state": result["overall_state"],
        "readiness_note": result["readiness_note"],
        "generated_at": result["generated_at"],
        "download_name": result["download_name"],
        "relative_export_path": result["relative_export_path"],
        "included_files": result["included_files"],
        "missing_album_fields": result["missing_album_fields"],
        "tracks": result["tracks"],
        "summary": result["summary"],
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_package": False,
        "master_audio_included": False,
        "assessment_type": "A2L_INTERNAL_RELEASE_READINESS",
    }


def _package_files(album: dict, readiness: dict, artifact_root: str | Path | None, stamp: str) -> tuple[dict[str, bytes], dict, dict]:
    files: dict[str, bytes] = {}
    manifest_path = default_manifest_path(album["release_id"], artifact_root)
    readiness_path = default_readiness_path(album["release_id"], artifact_root)
    if not manifest_path.is_file():
        raise ReleaseError("ALBUM_NOT_FOUND", "That album could not be found.")
    if not readiness_path.is_file():
        raise ExportError("READINESS_MISSING", "Album release readiness could not be written.")
    files["album/album_release_manifest.json"] = manifest_path.read_bytes()
    files["album/album_release_readiness.json"] = readiness_path.read_bytes()

    readiness_by_job = {
        str(item.get("ingest_job_id") or ""): item for item in readiness.get("tracks") or []
    }
    track_refs = []
    lyric_gaps = []
    optional_missing = []
    blocking_track_gaps = []
    for track in album.get("tracks") or []:
        position = int(track.get("position") or 0)
        job = str(track.get("ingest_job_id") or "")
        folder = _track_folder(position, track.get("song_title"))
        assessment = readiness_by_job.get(job) or {}
        song_payload, song_ref, audio_ref, lyrics_ref, lyric_files, lyrics_missing = _track_payload(
            track, artifact_root
        )
        if song_payload is not None:
            files[f"tracks/{folder}/{RECORD_FILENAME}"] = _json_bytes(song_payload)
        for name, body in lyric_files:
            files[f"tracks/{folder}/lyrics/{name}"] = body
        if lyrics_missing:
            lyric_gaps.append(
                {
                    "position": position,
                    "ingest_job_id": job,
                    "song_title": track.get("song_title"),
                    "status": "MISSING",
                }
            )
        for gap in assessment.get("blocking_missing_fields") or []:
            blocking_track_gaps.append({"position": position, "ingest_job_id": job, "song_title": track.get("song_title"), **gap})
        for gap in assessment.get("optional_missing_fields") or []:
            optional_missing.append({"position": position, "ingest_job_id": job, "song_title": track.get("song_title"), **gap})
        track_refs.append(
            {
                "position": position,
                "ingest_job_id": job,
                "package_track_folder": folder,
                "song_present": bool(track.get("song_present")),
                "song_release_record_ref": song_ref,
                "approved_lyrics_ref": lyrics_ref,
                "source_audio": audio_ref,
                "approved_lyrics_included": bool(lyric_files),
            }
        )

    completeness = {
        "overall_state": readiness.get("overall_state") or INCOMPLETE,
        "blocking_album_gaps": list(readiness.get("missing_album_fields") or []),
        "blocking_track_gaps": blocking_track_gaps,
        "optional_missing_fields": optional_missing,
        "missing_approved_lyrics": lyric_gaps,
        "tracks_requiring_correction": [
            {
                "position": item.get("position"),
                "ingest_job_id": item.get("ingest_job_id"),
                "song_title": item.get("song_title"),
                "release_readiness": item.get("release_readiness") or INCOMPLETE,
            }
            for item in readiness.get("tracks") or []
            if item.get("release_readiness") != READY
        ],
    }
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "kind": "DERIVED_EXPORT",
        "source_authority_kind": "SOURCE_AUTHORITY",
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_package": False,
        "master_audio_included": False,
        "generated_at": stamp,
        "release_id": album["release_id"],
        "album_manifest_ref": f"releases/{album['release_id']}/album_release_manifest.json",
        "album_readiness_ref": f"releases/{album['release_id']}/album_release_readiness.json",
        "tracks": track_refs,
        "notes": [
            "Derived A2L release-preparation package.",
            "This ZIP is not a metadata authority.",
            "Authoritative master audio was not copied into this package.",
            "Approved lyric words were not rewritten.",
            "Missing values were not invented.",
        ],
    }
    return files, completeness, provenance


def _track_payload(track: dict, artifact_root: str | Path | None) -> tuple:
    job = str(track.get("ingest_job_id") or "")
    song_ref = track.get("song_release_record_ref") or f"ingest/{job}/{RECORD_FILENAME}"
    audio_ref = _source_audio_ref(job, artifact_root)
    if not track.get("song_present"):
        return None, song_ref, audio_ref, None, [], True
    record = load_or_create_release_record(job, artifact_root=artifact_root, persist=False)
    lyrics_ref, lyric_files, lyrics_missing = _approved_lyric_exports(job, artifact_root, record)
    return record, song_ref, audio_ref, lyrics_ref, lyric_files, lyrics_missing


def _approved_lyric_exports(job: str, artifact_root: str | Path | None, record: dict) -> tuple[dict | None, list[tuple[str, bytes]], bool]:
    job_dir = _ingest_root(artifact_root) / job
    dirname = detect_pipeline_dirname(job_dir)
    approved_status = None
    for item in record.get("fields") or []:
        if item.get("id") == "approved_lyrics":
            approved_status = item.get("status")
            break
    txt_path = default_approved_txt_path(job, pipeline_dirname=dirname)
    json_path = default_approved_json_path(job, pipeline_dirname=dirname)
    lyrics_ref = None
    if txt_path.is_file() or json_path.is_file():
        lyrics_ref = {
            "approved_lyrics_txt_ref": _posix_relative(_artifact_root(artifact_root), txt_path) if txt_path.is_file() else None,
            "approved_lyrics_json_ref": _posix_relative(_artifact_root(artifact_root), json_path) if json_path.is_file() else None,
            "pipeline_dirname": dirname,
        }
    if approved_status != STATUS_AVAILABLE:
        return lyrics_ref, [], True
    lyric_files: list[tuple[str, bytes]] = []
    exports_dir = default_exports_dir(job, dirname)
    for format_id in SUPPORTED_FORMATS:
        name = INTERNAL_ARTIFACT_NAMES[format_id]
        existing = exports_dir / name
        if existing.is_file():
            lyric_files.append((name, existing.read_bytes()))
            continue
        try:
            rendered = format_approved_export(job, format_id, pipeline_dirname=dirname)
        except ExportError as exc:
            if exc.code == "NOT_APPROVED":
                return lyrics_ref, [], True
            raise
        lyric_files.append((name, rendered.text.encode("utf-8")))
    return lyrics_ref, lyric_files, not lyric_files


def _source_audio_ref(job: str, artifact_root: str | Path | None) -> dict:
    job_dir = _ingest_root(artifact_root) / job
    manifest_path = job_dir / MANIFEST_FILENAME
    source_path = job_dir / "authoritative_source" / SOURCE_FILENAME
    payload = {}
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    source = payload.get("authoritative_source") or {}
    digest = source.get("sha256") or payload.get("job_id")
    relative = source.get("relative_path")
    if not relative and source_path.is_file():
        relative = _posix_relative(job_dir, source_path)
    return {
        "included": False,
        "source_sha256": digest,
        "ingest_job_id": job or None,
        "ingest_manifest_ref": f"ingest/{job}/{MANIFEST_FILENAME}" if job else None,
        "authoritative_source_ref": f"ingest/{job}/{relative}" if job and relative else None,
    }


def _package_manifest(
    album: dict,
    readiness: dict,
    stamp: str,
    download_name: str,
    included: list[str],
    completeness: dict,
    provenance: dict,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "package_type": PACKAGE_TYPE,
        "package_version": PACKAGE_VERSION,
        "produced_by": PRODUCER_ACI,
        "authority": AUTHORITY,
        "kind": "DERIVED_EXPORT",
        "usable_as_approved_lyrics": False,
        "not_a_release_or_distribution": True,
        "distributor_package": False,
        "master_audio_included": False,
        "release_id": album["release_id"],
        "album_title": album.get("album_title"),
        "primary_artist": album.get("primary_artist"),
        "release_type": album.get("release_type"),
        "overall_state": readiness.get("overall_state"),
        "generated_at": stamp,
        "download_name": download_name,
        "included_files": included,
        "completeness": completeness,
        "source_authorities": {
            "album_release_manifest": provenance["album_manifest_ref"],
            "album_release_readiness": provenance["album_readiness_ref"],
            "song_release_records": [item.get("song_release_record_ref") for item in provenance.get("tracks") or []],
            "approved_lyrics": [item.get("approved_lyrics_ref") for item in provenance.get("tracks") or []],
            "source_audio": [item.get("source_audio") for item in provenance.get("tracks") or []],
        },
        "package_provenance": {
            "kind": "DERIVED_EXPORT",
            "source_authority_kind": "SOURCE_AUTHORITY",
            "generated_at": stamp,
            "release_id": album["release_id"],
        },
        "notes": [
            "A2L RELEASE PREPARATION PACKAGE.",
            DISCLAIMER,
            "Missing information is preserved. Values are not invented.",
            "Master WAV files are not included.",
        ],
    }


def _summary_text(album: dict, readiness: dict, completeness: dict, stamp: str) -> str:
    title = album.get("album_title") or "MISSING"
    artist = album.get("primary_artist") or "MISSING"
    release_type = album.get("release_type")
    type_label = RELEASE_TYPES.get(release_type or "", "MISSING") if release_type else "MISSING"
    tracks = album.get("tracks") or []
    lines = [
        "A2L RELEASE PREPARATION PACKAGE",
        DISCLAIMER,
        "",
        f"Album Title: {title}",
        f"Primary Artist: {artist}",
        f"Release Type: {type_label}",
        f"Track count: {len(tracks)}",
        "",
        "Ordered track listing:",
    ]
    if not tracks:
        lines.append("NONE")
    for item in tracks:
        position = int(item.get("position") or 0)
        song_title = item.get("song_title") or "MISSING"
        state = item.get("release_readiness") or INCOMPLETE
        lyrics = item.get("approved_lyrics_status") or "MISSING"
        lines.append(f"{position:02d}  {song_title}  {state}  Approved lyrics: {lyrics}")
    lines.extend(
        [
            "",
            "A2L INTERNAL RELEASE READINESS:",
            str(readiness.get("overall_state") or INCOMPLETE),
            "",
            "Blocking album gaps:",
        ]
    )
    album_gaps = completeness.get("blocking_album_gaps") or []
    if not album_gaps:
        lines.append("NONE")
    else:
        for gap in album_gaps:
            lines.append(f"- {gap.get('label') or gap.get('id')}  MISSING — BLOCKING")
    lines.extend(["", "Blocking track gaps:"])
    track_gaps = completeness.get("blocking_track_gaps") or []
    if not track_gaps:
        lines.append("NONE")
    else:
        for gap in track_gaps:
            pos = int(gap.get("position") or 0)
            song_title = gap.get("song_title") or "MISSING"
            lines.append(f"- Track {pos:02d} {song_title}: {gap.get('label') or gap.get('id')}  MISSING — BLOCKING")
    lines.extend(["", "Optional missing information:"])
    optional = completeness.get("optional_missing_fields") or []
    if not optional:
        lines.append("NONE")
    else:
        for gap in optional:
            pos = int(gap.get("position") or 0)
            song_title = gap.get("song_title") or "MISSING"
            lines.append(f"- Track {pos:02d} {song_title}: {gap.get('label') or gap.get('id')}  MISSING — OPTIONAL")
    lines.extend(["", "Tracks requiring correction:"])
    needing = completeness.get("tracks_requiring_correction") or []
    if not needing:
        lines.append("NONE")
    else:
        for item in needing:
            pos = int(item.get("position") or 0)
            song_title = item.get("song_title") or "MISSING"
            lines.append(f"- Track {pos:02d} {song_title}  {item.get('release_readiness') or INCOMPLETE}")
    lines.extend(["", "Missing approved lyrics:"])
    lyric_gaps = completeness.get("missing_approved_lyrics") or []
    if not lyric_gaps:
        lines.append("NONE")
    else:
        for item in lyric_gaps:
            pos = int(item.get("position") or 0)
            song_title = item.get("song_title") or "MISSING"
            lines.append(f"- Track {pos:02d} {song_title}  MISSING")
    lines.extend(
        [
            "",
            f"Package generated at: {stamp}",
            "",
            "A2L INTERNAL RELEASE READINESS disclaimer:",
            READINESS_NOTE,
        ]
    )
    return "\n".join(lines) + "\n"


def _write_zip(path: Path, files: dict[str, bytes], stamp: str) -> None:
    date_time = _zip_date(stamp)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = ZipInfo(filename=name.replace("\\", "/"), date_time=date_time)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, files[name])


def _track_folder(position: int, song_title) -> str:
    nn = f"{int(position):02d}"
    safe = _underscore_component(song_title)
    return f"{nn}_{safe}" if safe else f"{nn}_track"


def _underscore_component(value) -> str:
    text = sanitize_filename_component(value).replace(" ", "_")
    return "_".join(part for part in text.split("_") if part)


def _finalize_zip_name(name: str) -> str:
    candidate = Path(str(name or "").replace("\\", "/")).name
    candidate = candidate.replace("/", "").replace("\\", "").replace("\r", "").replace("\n", "")
    if not candidate.lower().endswith(".zip"):
        candidate = f"{candidate.rstrip('.')}.zip" if candidate else FALLBACK_ZIP_NAME
    stem = candidate[:-4].strip(" .")
    if not stem or stem in {".", ".."} or _reserved_windows_name(stem):
        return FALLBACK_ZIP_NAME
    if len(stem) > _MAX_STEM_CHARS:
        stem = stem[:_MAX_STEM_CHARS].rstrip(" .")
    return f"{stem}.zip"


def _reserved_windows_name(value: str) -> bool:
    stem = value.split(".")[0].upper()
    return stem in _WINDOWS_RESERVED


def _export_folder_name(generated_at: str) -> str:
    text = "".join(ch if ch.isalnum() else "-" for ch in str(generated_at or ""))
    return text.strip("-") or "export"


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _artifact_root(artifact_root: str | Path | None) -> Path:
    return Path(artifact_root) if artifact_root is not None else ROOT / "artifacts"


def _ingest_root(artifact_root: str | Path | None) -> Path:
    return _artifact_root(artifact_root) / "ingest"


def _posix_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _zip_date(stamp: str) -> tuple[int, int, int, int, int, int]:
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        return (parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute, parsed.second)
    except ValueError:
        now = datetime.now(timezone.utc)
        return (now.year, now.month, now.day, now.hour, now.minute, now.second)
