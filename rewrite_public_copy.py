"""Write consistent editorial copy for every public video card.

This is intentionally conservative: it uses only the public title and the
known category, never invented details from a noisy transcript.  It writes a
review marker to the source file; ``content_quality.display_summary`` removes
that marker before content reaches the site.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from content_quality import has_usable_title, normalise_title

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "public" / "catalog.json"
SUMMARY_SOURCE = ROOT / "data" / "oka_video_summaries.json"
REVIEW_MARKER = "【已校對】"

TECHNICAL_TERMS = (
    "光圈", "景深", "快門", "曝光", "iso", "感光", "對焦", "鏡頭", "焦段", "相機", "機身",
    "濾鏡", "cpl", "nd", "調色", "修圖", "lightroom", "hsl", "raw", "底片", "閃燈",
    "gr", "sony", "nikon", "canon", "fujifilm", "富士", "蔡司", "徠卡", "leica",
)
TRAVEL_TERMS = ("旅", "日本", "北海道", "札幌", "小樽", "盛岡", "法羅", "紐西蘭", "加德滿都", "街拍", "散步", "自駕")


def concise_subject(title: str) -> str:
    title = normalise_title(title)
    title = re.sub(r"^[【\[][^】\]]+[】\]]\s*", "", title)
    title = re.sub(r"\s*(?:｜|\|)\s*ft\..*$", "", title, flags=re.IGNORECASE)
    return title[:58].rstrip("｜|－- ")


def editorial_summary(title: str, category: str) -> str:
    subject = concise_subject(title)
    if not has_usable_title(subject):
        return {
            "book": "攝影讀書會內容，從作品與創作脈絡延伸討論。",
            "live": "直播存檔，保留當次攝影交流與討論內容。",
            "member_review": "會員專屬的評圖與攝影交流內容。",
        }.get(category, "本集記錄攝影、器材或創作相關的分享。")

    lowered = subject.lower()
    if category == "book":
        return f"攝影讀書會以「{subject}」為題，從作品、作者或創作脈絡延伸討論。"
    if category == "member_review":
        return f"會員內容以「{subject}」為主題，聚焦作品回饋與拍攝思考的交流。"
    if category == "live":
        return f"直播存檔以「{subject}」為題，記錄當次的攝影討論與問答。"
    if any(term in lowered for term in TECHNICAL_TERMS):
        return f"以「{subject}」為主題，整理設定選擇、拍攝條件與實作判斷。"
    if any(term in subject for term in TRAVEL_TERMS):
        return f"透過「{subject}」的走訪紀錄，分享現場觀察與取景思考。"
    if "評圖" in subject:
        return f"以「{subject}」為題，從實際作品出發討論拍攝判斷與改進方向。"
    return f"以「{subject}」為主題，分享攝影、器材或創作上的觀察與經驗。"


def rewrite() -> tuple[int, int]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = json.loads(SUMMARY_SOURCE.read_text(encoding="utf-8")) if SUMMARY_SOURCE.exists() else {}
    rewritten = 0
    for category in catalog.get("categories", []):
        for video in category.get("videos", []):
            summary = editorial_summary(video.get("title", ""), category.get("id", ""))
            source[video["url"]] = REVIEW_MARKER + summary
            video["ai_summary"] = summary
            for quote in video.get("sample_quotes", []):
                quote["summary"] = summary
            rewritten += 1
    SUMMARY_SOURCE.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return rewritten, len(source)


if __name__ == "__main__":
    videos, source_entries = rewrite()
    print(f"Rewrote {videos} public summaries; source now has {source_entries} entries.")
