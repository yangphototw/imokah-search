"""Repair only catalog titles proven wrong by a duplicate-ID collision.

The source title map is useful evidence, but is not blindly copied because
some entries are older English source titles.  A replacement is allowed only
when one public title is shared by multiple video IDs and the source map gives
that video a different non-empty title.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "public" / "catalog.json"
SOURCE = ROOT / "data" / "oka_youtube_map.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_title: dict[str, list[dict]] = defaultdict(list)
    for category in catalog["categories"]:
        for video in category["videos"]:
            by_title[video.get("title", "").strip()].append(video)

    repaired = []
    for title, videos in by_title.items():
        if len(videos) < 2:
            continue
        for video in videos:
            source_title = str(source.get(video["id"], {}).get("title", "")).strip()
            if source_title and source_title != title:
                repaired.append((video["id"], title, source_title))
                if args.apply:
                    video["title"] = source_title

    if args.apply:
        CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Proven duplicate-title repairs: {len(repaired)}")
    for video_id, old, new in repaired:
        print(f"{video_id}: {old} -> {new}")


if __name__ == "__main__":
    main()
