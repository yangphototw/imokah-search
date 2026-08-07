"""Restore damaged display titles from the original YouTube metadata map."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "public" / "catalog.json"
RAW_MAP = ROOT / "data" / "oka_youtube_map.json"
TITLE_MAP = ROOT / "data" / "oka_title_zh_mapping.json"


def is_damaged(title: str) -> bool:
    return len((title or "").strip()) < 4


def repair() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    raw_map = json.loads(RAW_MAP.read_text(encoding="utf-8"))
    title_map = json.loads(TITLE_MAP.read_text(encoding="utf-8"))
    repaired = 0
    for category in catalog.get("categories", []):
        for video in category.get("videos", []):
            video_id = video["id"]
            raw_title = raw_map.get(video_id, {}).get("title", "").strip()
            if is_damaged(video.get("title", "")) and not is_damaged(raw_title):
                title_map[video_id] = raw_title
                repaired += 1
    TITLE_MAP.write_text(json.dumps(title_map, ensure_ascii=False, indent=2), encoding="utf-8")
    return repaired


if __name__ == "__main__":
    print(f"Repaired {repair()} damaged display titles from oka_youtube_map.json.")
