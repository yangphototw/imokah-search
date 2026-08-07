"""Fast, dependency-free regression checks for the static Vercel deployment."""

import gzip
import json
from pathlib import Path

from build_static_search_index import (
    MAX_HITS_PER_TERM,
    MAX_SHARD_BYTES,
    MAX_TOTAL_INDEX_BYTES,
    SHARD_COUNT,
    shard_id,
)
from content_quality import display_summary

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
SHARDS = PUBLIC / "search-index"


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
    if manifest.get("shards") != SHARD_COUNT:
        fail(f"manifest shard count is {manifest.get('shards')}, expected {SHARD_COUNT}")
    if manifest.get("max_hits_per_term") != MAX_HITS_PER_TERM:
        fail("manifest does not enforce the expected per-term result limit")
    if len(list(SHARDS.glob("*.json.gz"))) != SHARD_COUNT:
        fail("generated shard file count does not match manifest")
    shard_files = list(SHARDS.glob("*.json.gz"))
    largest_shard = max(path.stat().st_size for path in shard_files)
    total_index_size = sum(path.stat().st_size for path in shard_files)
    if largest_shard > MAX_SHARD_BYTES:
        fail(f"largest shard is {largest_shard} bytes, over the deployment budget")
    if total_index_size > MAX_TOTAL_INDEX_BYTES:
        fail(f"static index is {total_index_size} bytes, over the deployment budget")

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
    for category_id, video in category_video_pairs:
        summary = video.get("ai_summary", "")
        if summary != display_summary(video["title"], summary, category_id):
            fail(f"catalog has unreviewed or low-quality public text: {video['id']}")
        if any(quote.get("summary") != summary for quote in video.get("sample_quotes", [])):
            fail(f"catalog quote text does not match its checked summary: {video['id']}")

    print(
        f"PASS: {len(videos)} videos; {manifest['terms']:,} search terms; "
        f"{SHARD_COUNT} shards; max {MAX_HITS_PER_TERM} hits/term; "
        f"{total_index_size / 1024 / 1024:.1f} MiB total"
    )


if __name__ == "__main__":
    main()
