"""Fast, dependency-free regression checks for the static Vercel deployment."""

import gzip
import json
from pathlib import Path

from build_static_search_index import (
    MAX_HITS_PER_TERM,
    MAX_HITS_PER_VIDEO_PER_TERM,
    MAX_SHARD_BYTES,
    MAX_TOTAL_INDEX_BYTES,
    SHARD_COUNT,
    paragraph_index_fingerprint,
    shard_id,
)
from content_quality import is_valid_public_summary

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
SHARDS = PUBLIC / "search-index"
PARAGRAPH_SHARDS = PUBLIC / "paragraph-index"
MAX_PARAGRAPH_INDEX_BYTES = 35 * 1024 * 1024


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_shard(term: str):
    path = SHARDS / f"{shard_id(term):03d}.json.gz"
    if not path.exists():
        fail(f"missing shard for {term!r}: {path.name}")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    manifest_path = SHARDS / "manifest.json"
    catalog_path = PUBLIC / "catalog.json"
    if not manifest_path.exists() or not catalog_path.exists():
        fail("static assets are missing; run build_static_search_index.py first")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != 3 or manifest.get("shards") != SHARD_COUNT:
        fail(f"manifest shard count is {manifest.get('shards')}, expected {SHARD_COUNT}")
    if manifest.get("max_hits_per_term") != MAX_HITS_PER_TERM:
        fail("manifest does not enforce the expected per-term result limit")
    if manifest.get("max_hits_per_video_per_term") != MAX_HITS_PER_VIDEO_PER_TERM:
        fail("manifest does not enforce the expected per-video result limit")
    if manifest.get("source") != "paragraph-index":
        fail("search index is not sourced from published paragraph context")
    if manifest.get("paragraph_index_sha256") != paragraph_index_fingerprint():
        fail("search index is stale relative to paragraph context")
    if len(list(SHARDS.glob("*.json.gz"))) != SHARD_COUNT:
        fail("generated shard file count does not match manifest")
    shard_files = list(SHARDS.glob("*.json.gz"))
    largest_shard = max(path.stat().st_size for path in shard_files)
    total_index_size = sum(path.stat().st_size for path in shard_files)
    if largest_shard > MAX_SHARD_BYTES:
        fail(f"largest shard is {largest_shard} bytes, over the deployment budget")
    if total_index_size > MAX_TOTAL_INDEX_BYTES:
        fail(f"static index is {total_index_size} bytes, over the deployment budget")

    paragraph_manifest_path = PARAGRAPH_SHARDS / "manifest.json"
    if not paragraph_manifest_path.exists():
        fail("paragraph context index is missing; run build_public_paragraph_index.py")
    paragraph_manifest = json.loads(paragraph_manifest_path.read_text(encoding="utf-8"))
    paragraph_files = list(PARAGRAPH_SHARDS.glob("*.json.gz"))
    if paragraph_manifest.get("shards") != SHARD_COUNT or len(paragraph_files) != SHARD_COUNT:
        fail("paragraph index shard count does not match the static deployment contract")
    paragraph_size = sum(path.stat().st_size for path in paragraph_files)
    if paragraph_size > MAX_PARAGRAPH_INDEX_BYTES:
        fail(f"paragraph context index is {paragraph_size} bytes, over the deployment budget")
    checked_paragraphs = 0
    for path in paragraph_files:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            shard = json.load(handle)
        for video_id, paragraphs in shard.items():
            if not isinstance(video_id, str) or len(video_id) != 11 or not isinstance(paragraphs, list):
                fail(f"invalid paragraph shard record: {path.name}")
            for paragraph in paragraphs:
                if not paragraph.get("id", "").startswith(f"{video_id}:"):
                    fail(f"paragraph has invalid provenance id: {path.name}")
                if float(paragraph.get("end", -1)) < float(paragraph.get("start", 0)):
                    fail(f"paragraph has inverted timestamps: {paragraph['id']}")
                if len(str(paragraph.get("transcript", ""))) < 24:
                    fail(f"paragraph is too short to replace a search excerpt: {paragraph['id']}")
                checked_paragraphs += 1
    if checked_paragraphs != paragraph_manifest.get("paragraphs"):
        fail("paragraph manifest count does not match the generated files")

    for term in ("光圈", "鏡頭", "a74", "iso"):
        hits = load_shard(term).get(term)
        if not hits:
            fail(f"expected search term missing from generated index: {term}")
        if len(hits) > MAX_HITS_PER_TERM:
            fail(f"search term exceeds result limit: {term}")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    category_video_pairs = [
        (category.get("id", ""), video)
        for category in catalog.get("categories", [])
        for video in category.get("videos", [])
    ]
    videos = [video for _, video in category_video_pairs]
    expected_count = catalog.get("channel_info", {}).get("total_videos")
    if not isinstance(expected_count, int) or expected_count <= 0:
        fail("catalog is missing a positive channel_info.total_videos")
    if len(videos) != expected_count:
        fail(f"catalog has {len(videos)} videos, expected {expected_count}")
    required = {"id", "title", "url"}
    if any(not required.issubset(video) for video in videos):
        fail("catalog contains a video missing id, title, or url")
    titles = [str(video["title"]).strip() for video in videos]
    if len(titles) != len(set(titles)):
        fail("catalog contains duplicate public video titles")
    processing_path = ROOT / "data" / "processing_manifest.json"
    if not processing_path.exists():
        fail("processing manifest is missing")
    processing = json.loads(processing_path.read_text(encoding="utf-8"))
    processing_videos = processing.get("videos", {})
    catalog_ids = {video["id"] for video in videos}
    if set(processing_videos) != catalog_ids:
        fail("processing manifest does not cover exactly the catalog videos")
    allowed_statuses = {"complete", "no_transcript_expected", "incomplete"}
    if any(record.get("status") not in allowed_statuses for record in processing_videos.values()):
        fail("processing manifest contains an unknown video status")
    if processing.get("counts", {}).get("covered") != len(videos):
        fail("not every catalog video is either content-complete or human-reviewed as non-verbal")
    app_source = (PUBLIC / "app.js").read_text(encoding="utf-8")
    if "summary: createClipListeningGuide(r.text, lastSearchQuery)" in app_source:
        fail("search clips still present transcript fragments as summaries")
    if "isTitleMatch: true" not in app_source:
        fail("title matches are not explicitly separated from transcript clips")
    if "attachParagraphContexts(results)" not in app_source or "完整逐字稿段落" not in app_source:
        fail("search UI does not resolve hits to complete paragraph transcripts")
    if "matchingTermGroupIndexes(title, termGroups)" not in app_source:
        fail("title cards do not retain the exact matched query terms")
    if "item.match_is_complete = matchedIndexes.length === totalTerms" not in app_source:
        fail("search results do not distinguish complete from partial matches")
    if "highlightSearchTerms(clip.transcript, clip.highlight_terms)" not in app_source:
        fail("transcript search terms are not visibly highlighted")
    for category_id, video in category_video_pairs:
        summary = video.get("ai_summary", "")
        if not is_valid_public_summary(summary, video["title"]):
            fail(f"catalog has low-quality public text: {video['id']}")
        if any(quote.get("summary") != summary for quote in video.get("sample_quotes", [])):
            fail(f"catalog quote text does not match its checked summary: {video['id']}")

    print(
        f"PASS: {len(videos)} videos; {manifest['terms']:,} search terms; "
        f"{SHARD_COUNT} shards; max {MAX_HITS_PER_TERM} hits/term; "
        f"{total_index_size / 1024 / 1024:.1f} MiB search + "
        f"{paragraph_size / 1024 / 1024:.1f} MiB paragraph context"
    )


if __name__ == "__main__":
    main()
