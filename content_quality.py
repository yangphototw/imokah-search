"""Quality gate for every summary string shown on the public site."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "public" / "catalog.json"
TRANSCRIPTS = ROOT / "data" / "transcripts"
REVIEW_QUEUE = ROOT / "data" / "summary_review_queue.json"

# These were produced by the former segment-level template pipeline.  They are
# not reliable statements about a whole video and must never reach a catalog card.
BAD_PHRASES = (
    "實務經驗與選單設定", "深入探討", "大家好", "我是道", "今天是我們",
    "之實務要點與應用心法", "對話精華：攝影話題交流", "對話觀點探討與心得分享",
)


def normalise_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip()).strip("｜|－- ")


def has_usable_title(title: str) -> bool:
    title = normalise_title(title)
    return len(title) >= 4 and title not in {"集", "影片", "直播"}


def is_publishable_summary(summary: str, title: str) -> bool:
    summary = (summary or "").strip()
    # Legacy output had no review provenance.  Only summaries explicitly
    # approved by the new curation workflow may make factual claims.
    if not summary.startswith("【已校對】"):
        return False
    summary = summary.removeprefix("【已校對】").strip()
    if not 18 <= len(summary) <= 90 or any(phrase in summary for phrase in BAD_PHRASES):
        return False
    return not summary.startswith("本集主題：") or has_usable_title(title)


def safe_topic_line(title: str, category: str) -> str:
    title = normalise_title(title)
    if has_usable_title(title):
        return f"本集主題：{title}"
    fallback = {
        "book": "本集為攝影讀書會內容，完整主題請至 YouTube 查看。",
        "live": "本集為直播內容，完整主題請至 YouTube 查看。",
        "member_review": "本集為會員評圖或討論內容，完整主題請至 YouTube 查看。",
    }
    return fallback.get(category, "本集影片主題請至 YouTube 查看。")


def display_summary(title: str, summary: str, category: str) -> str:
    """Return only public text that is safe and useful at video level."""
    if is_publishable_summary(summary, title):
        return summary.strip().removeprefix("【已校對】").strip()
    return safe_topic_line(title, category)


def transcript_evidence(video_id: str, limit: int = 8) -> list[dict[str, str]]:
    path = TRANSCRIPTS / f"{video_id}_transcript.json"
    if not path.exists():
        return []
    try:
        chunks = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    samples = []
    for chunk in chunks:
        text = re.sub(r"\s+", " ", str(chunk.get("text", "")).strip())
        if len(text) < 28 or any(x in text for x in ("大家好", "我是道", "訂閱", "按讚")):
            continue
        samples.append({"timestamp": str(chunk.get("timestamp", "00:00")), "text": text[:240]})
        if len(samples) == limit:
            break
    return samples


def rewrite_catalog() -> tuple[int, int]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    total = replaced = 0
    for category in catalog.get("categories", []):
        category_id = category.get("id", "")
        for video in category.get("videos", []):
            total += 1
            old = video.get("ai_summary", "")
            new = display_summary(video.get("title", ""), old, category_id)
            if new != old:
                replaced += 1
                video["ai_summary"] = new
                for quote in video.get("sample_quotes", []):
                    quote["summary"] = new
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return total, replaced


def build_review_queue() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    queue = []
    for category in catalog.get("categories", []):
        for video in category.get("videos", []):
            queue.append({
                "video_id": video["id"], "title": video.get("title", ""),
                "category": category.get("id", ""), "url": video.get("url", ""),
                "current_display_text": video.get("ai_summary", ""),
                "evidence": transcript_evidence(video["id"]), "status": "needs_curated_summary",
            })
    REVIEW_QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(queue)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit public catalog text and build a summary review queue")
    parser.add_argument("--rewrite-catalog", action="store_true")
    parser.add_argument("--build-review-queue", action="store_true")
    args = parser.parse_args()
    if args.rewrite_catalog:
        total, replaced = rewrite_catalog()
        print(f"Catalog quality gate: {replaced}/{total} summary strings replaced.")
    if args.build_review_queue:
        print(f"Review queue: {build_review_queue()} videos written to {REVIEW_QUEUE.name}.")
