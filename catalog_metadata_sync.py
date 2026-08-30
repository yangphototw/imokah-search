"""Synchronize verified YouTube publish dates into the public video catalog.

This tool intentionally requests metadata only.  It never downloads media,
changes transcripts, or fabricates a date when YouTube does not expose one.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from channel_update import discovery_options


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "public" / "catalog.json"
DATE_MAP = ROOT / "data" / "oka_youtube_dates.json"
DATE_PATTERN = re.compile(r"^\d{8}$")


def load_json(path: Path, default: object) -> object:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def iso_date(upload_date: object) -> str:
    """Return an ISO date only when YouTube supplied a complete YYYYMMDD value."""
    value = str(upload_date or "")
    if not DATE_PATTERN.fullmatch(value):
        return ""
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def catalog_by_id(catalog: dict) -> dict[str, dict]:
    return {
        str(video.get("id", "")): video
        for category in catalog.get("categories", [])
        for video in category.get("videos", [])
        if video.get("id")
    }


def missing_publish_date_ids(catalog: dict) -> list[str]:
    return sorted(
        video_id
        for video_id, video in catalog_by_id(catalog).items()
        if not str(video.get("publish_date", "")).strip()
    )


def fetch_upload_dates(video_ids: list[str]) -> dict[str, str]:
    """Fetch individual video metadata, tolerating private/member-only failures."""
    if not video_ids:
        return {}
    from yt_dlp import YoutubeDL

    options = discovery_options()
    options.update({"ignoreerrors": True, "noplaylist": True, "quiet": True, "skip_download": True})
    resolved: dict[str, str] = {}
    with YoutubeDL(options) as ydl:
        for video_id in video_ids:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            if date := iso_date((info or {}).get("upload_date", "")):
                resolved[video_id] = date
    return resolved


def merge_publish_dates(catalog: dict, date_map: dict[str, str], resolved: dict[str, str]) -> list[str]:
    """Fill blank catalog dates from verified values and return changed video IDs."""
    videos = catalog_by_id(catalog)
    changed: list[str] = []
    for video_id, publish_date in resolved.items():
        video = videos.get(video_id)
        if video is None:
            continue
        if not str(video.get("publish_date", "")).strip():
            video["publish_date"] = publish_date
            changed.append(video_id)
        if not str(date_map.get(video_id, "")).strip():
            date_map[video_id] = publish_date
    return changed


def atomic_json_write(path: Path, payload: object, *, indent: int | None = None) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
    temporary.write_text(serialized + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill blank public catalog dates from YouTube metadata")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report verified dates without changing files")
    mode.add_argument("--apply", action="store_true", help="Write only verified dates into the catalog and date map")
    args = parser.parse_args()

    catalog = load_json(CATALOG, {})
    if not isinstance(catalog, dict):
        raise ValueError(f"Invalid catalog payload: {CATALOG}")
    date_map = load_json(DATE_MAP, {})
    if not isinstance(date_map, dict):
        raise ValueError(f"Invalid date map payload: {DATE_MAP}")

    missing_ids = missing_publish_date_ids(catalog)
    resolved = fetch_upload_dates(missing_ids)
    unresolved = [video_id for video_id in missing_ids if video_id not in resolved]
    changed = merge_publish_dates(catalog, date_map, resolved)

    print(
        f"Catalog total: {len(catalog_by_id(catalog))}; blank dates before sync: {len(missing_ids)}; "
        f"verified: {len(changed)}; still unavailable: {len(unresolved)}."
    )
    for video_id in changed:
        print(f"VERIFIED {video_id} {resolved[video_id]}")
    for video_id in unresolved:
        print(f"UNAVAILABLE {video_id}")

    if args.apply and changed:
        atomic_json_write(CATALOG, catalog)
        atomic_json_write(DATE_MAP, date_map, indent=2)
        print(f"Applied {len(changed)} verified publish dates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
