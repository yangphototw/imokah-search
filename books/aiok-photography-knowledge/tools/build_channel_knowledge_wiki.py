#!/usr/bin/env python3
"""Build the chapter map, curated points and complete channel video notes.

Teaching claims come only from the maintained evidence-bound editorial JSON.
Proposed lessons remain separate and never enter the keyword dictionary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "books" / "aiok-photography-knowledge"
CATALOG_PATH = BOOK / "corpus" / "video-knowledge-catalog.json"
PUBLIC_CATALOG_PATH = ROOT / "public" / "catalog.json"
CARDS_DIR = BOOK / ".cangjie" / "capabilities" / "cards"
# The production-compatible output lives underneath the existing static site.
# It is served by Vercel as /wiki/ without requiring a second project.
OUTPUT_DIR = ROOT / "public" / "wiki"


CURATED_PATH = BOOK / "wiki" / "knowledge-points.json"
CURATED = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
HUBS = CURATED["hubs"]
from wiki_evidence import load_rows, validate_points


def normalise(value: str) -> str:
    return value.lower().replace("－", "-").replace("　", " ")


def classify(video: dict) -> tuple[str, list[str]]:
    approved = video.get("approved_summary") or {}
    summary = approved.get("summary", "")
    haystack = normalise(" ".join([video.get("title", ""), summary, video.get("category_name", "")]))
    scores: dict[str, int] = {}
    for hub in HUBS:
        score = sum(1 for keyword in hub["keywords"] if normalise(keyword) in haystack)
        scores[hub["id"]] = score
    high_score = max(scores.values(), default=0)
    if high_score == 0:
        return "creative", ["creative"]
    ordered = sorted(HUBS, key=lambda hub: (-scores[hub["id"]], hub["number"]))
    primary = ordered[0]["id"]
    tags = [hub["id"] for hub in ordered if scores[hub["id"]] > 0]
    return primary, tags[:3]


def time_label(seconds: float | int | None) -> str:
    if seconds is None:
        return "來源段落"
    seconds = int(float(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def youtube_url(video_id: str, start: float | int | None) -> str:
    base = f"https://www.youtube.com/watch?v={video_id}"
    return f"{base}&t={int(float(start))}s" if start is not None else base


def make_video_note(video: dict) -> dict:
    primary_hub, tags = classify(video)
    approved = video.get("approved_summary") or {}
    evidence = [
        {
            "label": time_label(item.get("start")),
            "url": youtube_url(video["id"], item.get("start")),
            "paragraph_id": item.get("paragraph_id"),
        }
        for item in approved.get("evidence", [])
    ]
    exception = video.get("review_exception") or {}
    return {
        "id": video["id"],
        "title": video.get("title", "未命名影片"),
        "url": video.get("url") or youtube_url(video["id"], None),
        "date": video.get("publish_date"),
        "category": video.get("category_name") or "未分類",
        "primary_hub": primary_hub,
        "tags": tags,
        "kind": "approved" if approved else "exception",
        "summary": approved.get("summary") or exception.get("human_summary") or exception.get("suggested_summary") or "這支影片尚待人工補寫摘要；請由原始影片與逐字稿確認內容。",
        "evidence": evidence,
        "transcript_status": video.get("transcript_status"),
        "member_only": bool(video.get("is_member_only")),
    }


def html_template() -> str:
    return (BOOK / "wiki" / "site" / "index.html").read_text(encoding="utf-8")


def build(output_dir: Path) -> dict:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    public_catalog = json.loads(PUBLIC_CATALOG_PATH.read_text(encoding="utf-8"))
    videos = [make_video_note(video) for video in catalog["videos"]]
    # ISO dates sort lexically.  Missing dates deliberately receive a floor value,
    # so fresh uploads remain at the top of the complete catalogue.
    videos.sort(key=lambda item: (item["date"] or "0000-00-00", item["title"]), reverse=True)
    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    rows = load_rows()
    evidence_count = validate_points(curated, rows)
    articles = curated["articles"]
    frameworks = []
    source_guides = articles
    article_hubs = {article["hub"] for article in articles}
    states = Counter(video["kind"] for video in videos)
    processed_ids = {video["id"] for video in videos}
    channel_catalog_ids = {
        str(video["id"])
        for category in public_catalog["categories"]
        for video in category["videos"]
    }
    pending_pipeline_ids = sorted(channel_catalog_ids - processed_ids)
    corpus_only_ids = sorted(processed_ids - channel_catalog_ids)
    manifest_path = BOOK / "corpus" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    payload = {
        "schema_version": 4,
        "hubs": [{key: value for key, value in hub.items() if key != "keywords"} for hub in HUBS],
        "subjects": curated.get("subjects", []),
        "articles": articles,
        "videos": videos,
        "stats": {
            "built_at": date.today().isoformat(),
            "total_videos": len(channel_catalog_ids),
            "processed_videos": len(videos),
            "pending_pipeline_videos": len(pending_pipeline_ids),
            "approved_summaries": states["approved"],
            "review_exceptions": states["exception"],
            "reading_articles": len(articles),
            "evidence_references": evidence_count,
            "verified_framework_articles": len(frameworks),
            "source_guides": len(source_guides),
            "article_chapters": len(article_hubs),
            # Corpus manifests expose this as `indexed_passages`.  Retain the
            # old spelling only as a compatibility fallback for older builds.
            "passage_count": manifest.get("indexed_passages", manifest.get("passage_count", 60045)),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset in ("wiki.css", "wiki.js"):
        (output_dir / asset).write_text((BOOK / "wiki" / "site" / asset).read_text(encoding="utf-8"), encoding="utf-8")
    lexicon = {"version": 1, "points": [
        {**{k: a[k] for k in ("id", "hub", "display_title", "lead", "keywords", "questions")},
         "subjects": a.get("subjects", []),
         "url": "/wiki/#point=" + a["id"]} for a in articles]}
    (output_dir / "knowledge-lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    topics = [{"id": a["id"], "chapter": next(h["title"] for h in HUBS if h["id"] == a["hub"]),
               "title": a["display_title"], "question": a["gap"]["question"]} for a in articles]
    (output_dir / "request-topics.json").write_text(json.dumps(topics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    data_script = "window.CHANNEL_KNOWLEDGE_WIKI = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (output_dir / "channel-knowledge-wiki-data.js").write_text(data_script, encoding="utf-8")
    # The stable filename changes on every intake. A content version prevents
    # a returning browser from pairing a new Wiki page with an old corpus.
    data_version = hashlib.sha256(data_script.encode("utf-8")).hexdigest()[:16]
    html = html_template().replace('src="channel-knowledge-wiki-data.js"',
        f'src="channel-knowledge-wiki-data.js?v={data_version}"')
    for name in ("wiki.css", "wiki.js", "request-config.js", "lesson-requests.js", "../style.css", "../site-shell.css", "../site-shell.js", "../knowledge-search.js"):
        path = output_dir / name if name in ("wiki.css", "wiki.js") else OUTPUT_DIR / name
        version = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        html = re.sub(r'((?:src|href)="' + re.escape(name) + r')(?:\?v=[^"]*)?"', lambda match: match.group(1) + f'?v={version}"', html)
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    coverage = {
        "built_at": payload["stats"]["built_at"],
        "channel_catalog_total": len(channel_catalog_ids),
        "processed_videos": len(videos),
        "pending_pipeline_ids": pending_pipeline_ids,
        "corpus_only_ids": corpus_only_ids,
        "approved_summaries": states["approved"],
        "review_exceptions": states["exception"],
        "chapter_counts": {hub["id"]: sum(1 for video in videos if video["primary_hub"] == hub["id"]) for hub in HUBS},
        "reading_articles": [article["id"] for article in articles],
        "verified_framework_articles": [card["id"] for card in frameworks],
        "source_guides": [guide["id"] for guide in source_guides],
        "article_hubs": sorted(article_hubs),
        "integrity": {
            "all_knowledge_evidence_current": evidence_count > 0,
            "all_videos_assigned_once": len(videos) == sum(1 for video in videos if video.get("primary_hub") in {hub["id"] for hub in HUBS}),
            "approved_plus_exceptions_equals_processed": states["approved"] + states["exception"] == len(videos),
            "channel_catalog_reconciled": not pending_pipeline_ids and not corpus_only_ids,
            "all_chapters_have_reading_article": article_hubs == {hub["id"] for hub in HUBS},
        },
    }
    (output_dir / "WIKI_COVERAGE.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--validate", action="store_true", help="Build then verify the generated JSON payload.")
    args = parser.parse_args()
    coverage = build(args.output)
    if args.validate:
        payload_path = args.output / "channel-knowledge-wiki-data.js"
        raw = payload_path.read_text(encoding="utf-8")
        prefix = "window.CHANNEL_KNOWLEDGE_WIKI = "
        assert raw.startswith(prefix) and raw.rstrip().endswith(";"), "Unexpected JavaScript payload wrapper"
        payload = json.loads(raw[len(prefix):].rstrip().removesuffix(";"))
        assert len(payload["videos"]) == payload["stats"]["processed_videos"], "Processed corpus count mismatch"
        assert payload["stats"]["total_videos"] == payload["stats"]["processed_videos"] + payload["stats"]["pending_pipeline_videos"], "Channel count mismatch"
        assert payload["stats"]["approved_summaries"] + payload["stats"]["review_exceptions"] == payload["stats"]["processed_videos"]
        assert coverage["integrity"]["all_videos_assigned_once"]
        assert coverage["integrity"]["all_chapters_have_reading_article"], "Every chapter needs a reading article"
        assert all(article.get("sources") for article in payload["articles"]), "Every article needs source links"
    print(json.dumps(coverage, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
