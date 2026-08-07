"""Fetch current YouTube titles for only catalog/source disagreements.

Results are resumable local audit evidence.  The script never changes the
catalog; title changes require a separate review decision.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".python-packages"))

from yt_dlp import YoutubeDL

CATALOG = ROOT / "public" / "catalog.json"
SOURCE = ROOT / "data" / "oka_youtube_map.json"
OUTPUT = ROOT / "data" / "current_youtube_title_audit.json"


def mismatches() -> list[tuple[str, str, str]]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = []
    for category in catalog["categories"]:
        for video in category["videos"]:
            video_id = video["id"]
            catalog_title = str(video.get("title", "")).strip()
            source_title = str(source.get(video_id, {}).get("title", "")).strip()
            if source_title and source_title != catalog_title:
                items.append((video_id, catalog_title, source_title))
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0 fetches every pending title.")
    parser.add_argument("--apply", action="store_true", help="Apply only fetched current titles to the catalog.")
    args = parser.parse_args()
    existing = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    pending = [item for item in mismatches() if item[0] not in existing]
    if args.limit:
        pending = pending[:args.limit]
    print(f"Pending current-title checks: {len(pending)}")

    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    with YoutubeDL(options) as ydl:
        for video_id, catalog_title, source_title in pending:
            url = f"https://www.youtube.com/watch?v={video_id}"
            record = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "catalog_title": catalog_title,
                "source_title": source_title,
            }
            try:
                info = ydl.extract_info(url, download=False)
                record["current_title"] = str(info.get("title", "")).strip()
                record["status"] = "fetched" if record["current_title"] else "empty_title"
            except Exception as exc:
                record["status"] = "unavailable"
                record["error"] = str(exc)
            existing[video_id] = record
            OUTPUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{video_id}: {record['status']}")

    if args.apply:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        changed = 0
        for category in catalog["categories"]:
            for video in category["videos"]:
                current = existing.get(video["id"], {})
                title = current.get("current_title", "")
                if current.get("status") == "fetched" and title and title != video.get("title", ""):
                    video["title"] = title
                    changed += 1
        CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"Applied current YouTube titles: {changed}")


if __name__ == "__main__":
    main()
