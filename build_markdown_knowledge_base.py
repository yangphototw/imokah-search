"""Build a human-readable, evidence-first Markdown knowledge base.

This deliberately does not use legacy template summaries.  Every generated
entry is either a timestamped transcript paragraph or an explicit human review
record for a non-verbal video.  The documents are meant to be read directly or
searched with a normal editor / GitHub code search.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
PARAGRAPHS = PUBLIC / "paragraph-index"
CATALOG = PUBLIC / "catalog.json"
PROCESSING = ROOT / "data" / "processing_manifest.json"
EXEMPTIONS = ROOT / "data" / "transcript_exemptions.json"
KNOWLEDGE = ROOT / "knowledge"
VIDEOS = KNOWLEDGE / "videos"
TOPICS = KNOWLEDGE / "topics"

TOPIC_RULES = {
    "exposure": ("曝光與測光", ("ISO", "EV", "\u5149\u5708", "\u5feb\u9580", "\u6e2c\u5149")),
    "focus": ("對焦與鏡頭", ("AF", "\u5c0d\u7126", "\u93e1\u982d", "mm", "\u7126\u6bb5")),
    "composition": ("構圖與創作", ("\u69cb\u5716", "\u8996\u89d2", "\u8272\u5f69", "\u5149\u5f71", "\u8857\u62cd")),
    "editing": ("後製與工作流程", ("Lightroom", "Photoshop", "LUT", "\u5f8c\u88fd", "\u8abf\u8272")),
    "gear": ("器材與相機", ("Sony", "Nikon", "Canon", "Fujifilm", "Ricoh", "Leica", "\u76f8\u6a5f")),
    "travel": ("旅行與實拍", ("\u65c5\u884c", "\u98a8\u666f", "\u65c5\u904a", "\u8857\u62cd", "\u6d3b\u52d5")),
    "business": ("職業與器材選擇", ("\u5a5a\u79ae", "\u63a5\u6848", "\u9810\u7b97", "\u8cfc\u8cb7", "\u5be6\u6e2c")),
}
CLAIM_CUES = ("\u4e00\u5b9a", "\u7d55\u5c0d", "\u6c38\u9060", "\u5fc5\u9808", "\u552f\u4e00", "\u4e0d\u6703", "\u90fd\u6703")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 60:02d}:{value % 60:02d}"


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def escaped(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def load_catalog() -> dict[str, dict]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {
        video["id"]: video
        for category in catalog["categories"]
        for video in category["videos"]
    }


def load_paragraphs() -> dict[str, list[dict]]:
    result = {}
    for path in PARAGRAPHS.glob("*.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            result.update(json.load(handle))
    return result


def topic_keys(title: str, transcript: str) -> list[str]:
    text = f"{title} {transcript}".lower()
    return [key for key, (_, terms) in TOPIC_RULES.items() if any(term.lower() in text for term in terms)] or ["uncategorized"]


def source_link(video_id: str, start: float) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"


def build() -> dict:
    catalog = load_catalog()
    paragraphs = load_paragraphs()
    processing = json.loads(PROCESSING.read_text(encoding="utf-8"))
    exemptions = json.loads(EXEMPTIONS.read_text(encoding="utf-8")).get("videos", {})
    by_topic: dict[str, list[dict]] = defaultdict(list)
    claim_candidates = []
    video_count = 0
    passage_count = 0

    for video_id, video in sorted(catalog.items(), key=lambda item: item[1]["title"]):
        title = compact(video["title"])
        status = processing["videos"][video_id]["status"]
        records = paragraphs.get(video_id, [])
        lines = [
            f"# {title}",
            "",
            f"- Video: [{video_id}](https://www.youtube.com/watch?v={video_id})",
            f"- Knowledge status: `{status}`",
        ]
        if status == "no_transcript_expected":
            review = exemptions.get(video_id, {})
            lines.extend([
                f"- Human review: {review.get('note', 'No spoken transcript expected')}",
                "",
                "This video is intentionally indexed by title and metadata only; no transcript or factual summary is inferred from its audio.",
            ])
        else:
            lines.extend(["", "## Timestamped transcript evidence", ""])
            for entry in records:
                text = compact(entry.get("transcript", ""))
                if not text:
                    continue
                start = float(entry["start"])
                link = source_link(video_id, start)
                lines.extend([f"### [{timestamp(start)}]({link})", "", text, ""])
                labels = topic_keys(title, text)
                for label in labels:
                    by_topic[label].append({"video_id": video_id, "title": title, "start": start})
                if any(cue in text for cue in CLAIM_CUES) and any(label != "uncategorized" for label in labels):
                    claim_candidates.append({
                        "video_id": video_id, "title": title, "start": start,
                        "text": text, "topics": labels,
                    })
                passage_count += 1
        write(VIDEOS / f"{video_id}.md", "\n".join(lines).rstrip() + "\n")
        video_count += 1

    write(KNOWLEDGE / "README.md", """# 我都 OK 啊：可追溯知識庫

這是一份由全頻道逐字稿段落建立的 Markdown 字典。每一則內容都必須回到影片與時間點；它不是自動生成的事實百科。

## 使用方式

- 依影片查閱：[`videos/`](videos/)
- 依主題查閱：[`topics/`](topics/)
- 需要事實核對的候選說法：[`FACT_CHECK_QUEUE.md`](FACT_CHECK_QUEUE.md)
- 資料品質與已排除的舊摘要：[`ERRATA.md`](ERRATA.md)

## 信任規則

1. 「逐字稿證據」表示影片說了什麼，不等於該說法已被外部證實。
2. 具體規格、價格、產品功能、健康／法律／財務建議，必須另查一手來源才可寫為事實。
3. 無人聲影片只保留人工確認的類型與影片連結；不推測影片內容。
""")

    index_lines = ["# 影片索引", "", "| 影片 | 狀態 |", "| --- | --- |"]
    for video_id, video in sorted(catalog.items(), key=lambda item: item[1]["title"]):
        status = processing["videos"][video_id]["status"]
        index_lines.append(f"| [{escaped(compact(video['title']))}](videos/{video_id}.md) | `{status}` |")
    write(KNOWLEDGE / "INDEX.md", "\n".join(index_lines) + "\n")

    for key, (label, _) in TOPIC_RULES.items():
        lines = [f"# {label}", "", "每列都是可回查的逐字稿證據，不是已驗證結論。", ""]
        for entry in sorted(by_topic[key], key=lambda item: (item["title"], item["start"])):
            link = source_link(entry["video_id"], entry["start"])
            lines.append(f"- [{entry['title']} · {timestamp(entry['start'])}]({link}) · [evidence page](../videos/{entry['video_id']}.md)")
        write(TOPICS / f"{key}.md", "\n".join(lines) + "\n")

    queue_lines = [
        "# 待事實核對說法", "",
        "以下是包含絕對語氣且涉及攝影主題的逐字稿候選。它們**不是錯誤判定**；在取得一手資料前，不應寫入結論型知識庫。",
        "",
    ]
    for item in claim_candidates:
        link = source_link(item["video_id"], item["start"])
        queue_lines.extend([
            f"## [{item['title']} · {timestamp(item['start'])}]({link})",
            "",
            f"Topics: `{', '.join(item['topics'])}` · [full evidence page](videos/{item['video_id']}.md)", "",
        ])
    write(KNOWLEDGE / "FACT_CHECK_QUEUE.md", "\n".join(queue_lines))
    write(KNOWLEDGE / "ERRATA.md", """# 資料品質與已知問題

## 已排除：關鍵字模板摘要

舊檔 `data/oka_ai_summaries.json` 與其產生器以關鍵字套用通用句型，無法證明內容來自影片。因此它們不可作為本知識庫、公開摘要或事實核對的來源。

## 逐字稿限制

逐字稿是 ASR 證據，仍可能有同音字、專有名詞或數字錯誤。任何技術規格與絕對結論都需以影片音訊和官方文件再次核對。

## 無人聲影片

已由人工確認為無人聲或環境音的影片，會標示 `no_transcript_expected`，不會被模型虛構摘要。
""")

    manifest = {
        "version": 1,
        "videos": video_count,
        "passages": passage_count,
        "fact_check_candidates": len(claim_candidates),
        "catalog_hash": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "processing_hash": hashlib.sha256(PROCESSING.read_bytes()).hexdigest(),
    }
    write(KNOWLEDGE / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
