"""Fast, dependency-free regression checks for the static Vercel deployment."""

import gzip
import json
from pathlib import Path

from build_static_search_index import SHARD_COUNT, shard_id

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
    if len(list(SHARDS.glob("*.json.gz"))) != SHARD_COUNT:
        fail("generated shard file count does not match manifest")

    for term in ("光圈", "鏡頭", "a74", "iso"):
        if term not in load_shard(term):
            fail(f"expected search term missing from generated index: {term}")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    videos = [video for category in catalog.get("categories", []) for video in category.get("videos", [])]
    if len(videos) != 1038:
        fail(f"catalog has {len(videos)} videos, expected 1038")
    required = {"id", "title", "url"}
    if any(not required.issubset(video) for video in videos):
        fail("catalog contains a video missing id, title, or url")

    print(f"PASS: {len(videos)} videos; {manifest['terms']:,} search terms; {SHARD_COUNT} shards")


if __name__ == "__main__":
    main()
