"""Apply only high-confidence title-based corrections to public categories."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_MAP = ROOT / "data" / "oka_youtube_map.json"
TITLE_MAP = ROOT / "data" / "oka_title_zh_mapping.json"
CATEGORY_MAP = ROOT / "data" / "oka_gemini_categories.json"


def category_from_title(title: str) -> str | None:
    title = (title or "").lower()
    if "讀書會" in title:
        return "book"
    if "會員" in title and "評圖" in title:
        return "member_review"
    if "直播" in title:
        return "live"
    return None


def repair() -> int:
    raw_map = json.loads(RAW_MAP.read_text(encoding="utf-8"))
    title_map = json.loads(TITLE_MAP.read_text(encoding="utf-8"))
    categories = json.loads(CATEGORY_MAP.read_text(encoding="utf-8"))
    changed = 0
    for video_id, meta in raw_map.items():
        title = title_map.get(video_id) or meta.get("title", "")
        corrected = category_from_title(title)
        if corrected and categories.get(video_id) != corrected:
            categories[video_id] = corrected
            changed += 1
    CATEGORY_MAP.write_text(json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


if __name__ == "__main__":
    print(f"Corrected {repair()} high-confidence category assignments.")
