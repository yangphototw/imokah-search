"""Update only the CDN search shards touched by newly published paragraphs."""

import gzip
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from build_static_search_index import (
    MAX_HITS_PER_TERM,
    MAX_HITS_PER_VIDEO_PER_TERM,
    PUBLIC,
    SHARD_COUNT,
    paragraph_index_fingerprint,
    shard_id,
)
from build_public_paragraph_index import shard_id_for_video

ROOT = Path(__file__).resolve().parent
SHARDS = PUBLIC / "search-index"
PARAGRAPH_SHARDS = PUBLIC / "paragraph-index"
MANIFEST = SHARDS / "manifest.json"
CATALOG = PUBLIC / "catalog.json"
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]{1,4}")


def atomic_json_gzip_write(path: Path, payload: dict) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as raw_handle:
            with gzip.GzipFile(fileobj=raw_handle, mode="wb", compresslevel=9) as gzip_handle:
                gzip_handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def atomic_json_write(path: Path, payload: dict) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def tokens_for_paragraph(paragraph: dict) -> set[str]:
    content = str(paragraph.get("transcript", "")).lower()
    return set(TOKEN_PATTERN.findall(content))


def load_shard(number: int) -> dict:
    path = SHARDS / f"{number:03d}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def build_video_hits(video_ids: list[str]) -> tuple[dict[str, list[list]], set[int]]:
    term_hits: dict[str, list[list]] = defaultdict(list)
    touched_shards: set[int] = set()

    for video_id in video_ids:
        paragraph_path = PARAGRAPH_SHARDS / f"{shard_id_for_video(video_id):03d}.json.gz"
        if not paragraph_path.exists():
            raise FileNotFoundError(f"Paragraph index missing for {video_id}: {paragraph_path}")
        with gzip.open(paragraph_path, "rt", encoding="utf-8") as handle:
            paragraphs = json.load(handle).get(video_id)
        if paragraphs is None:
            raise FileNotFoundError(f"Paragraph context missing for {video_id}")
        for paragraph in paragraphs:
            start = float(paragraph.get("start", 0) or 0)
            hit = [
                video_id,
                f"{int(start // 60):02d}:{int(start % 60):02d}",
                "",
                start,
            ]
            for term in tokens_for_paragraph(paragraph):
                term_hits[term].append(hit)
                touched_shards.add(shard_id(term))
    return term_hits, touched_shards


def merge_hits(new_hits: list[list], existing_hits: list[list]) -> list[list]:
    """Prefer fresh paragraphs while preserving result diversity and size limits."""
    merged = []
    seen = set()
    per_video = defaultdict(int)
    for hit in new_hits + existing_hits:
        key = (hit[0], hit[1])
        if key not in seen and per_video[hit[0]] < MAX_HITS_PER_VIDEO_PER_TERM:
            seen.add(key)
            merged.append(hit)
            per_video[hit[0]] += 1
            if len(merged) == MAX_HITS_PER_TERM:
                break
    return merged


def rebuild_catalog() -> None:
    # Import lazily so a static-site-only workflow does not load legacy search
    # data until this small catalog has to be regenerated.
    from web_server import build_encyclopedia_data

    catalog = build_encyclopedia_data()
    # The legacy catalog generator may collapse several historical titles into
    # one generic label.  Restore only proven collisions from the source map;
    # this keeps future incremental updates from reintroducing duplicates.
    source_path = ROOT / "data" / "oka_youtube_map.json"
    source = json.loads(source_path.read_text(encoding="utf-8")) if source_path.exists() else {}
    by_title: dict[str, list[dict]] = defaultdict(list)
    for category in catalog.get("categories", []):
        for video in category.get("videos", []):
            by_title[str(video.get("title", "")).strip()].append(video)
    for title, videos in by_title.items():
        if len(videos) < 2:
            continue
        for video in videos:
            replacement = str(source.get(video.get("id", ""), {}).get("title", "")).strip()
            if replacement and replacement != title:
                video["title"] = replacement
    atomic_json_write(CATALOG, catalog)


def refresh_manifest() -> None:
    file_counts = {}
    total_terms = 0
    for number in range(SHARD_COUNT):
        shard = load_shard(number)
        filename = f"{number:03d}.json.gz"
        file_counts[filename] = len(shard)
        total_terms += len(shard)
    manifest = {
        "version": 3,
        "shards": SHARD_COUNT,
        "terms": total_terms,
        "max_hits_per_term": MAX_HITS_PER_TERM,
        "max_hits_per_video_per_term": MAX_HITS_PER_VIDEO_PER_TERM,
        "source": "paragraph-index",
        "paragraph_index_sha256": paragraph_index_fingerprint(),
        "files": file_counts,
    }
    atomic_json_write(MANIFEST, manifest)


def update_for_new_videos(video_ids: list[str]) -> int:
    """Add new videos without reading the full RAG or inverted-index datasets."""
    if not video_ids:
        return 0
    if not SHARDS.exists():
        raise FileNotFoundError("Static search index is missing; run build_static_search_index.py once first")

    term_hits, touched_shards = build_video_hits(video_ids)
    grouped_terms: dict[int, dict[str, list[list]]] = defaultdict(dict)
    for term, hits in term_hits.items():
        grouped_terms[shard_id(term)][term] = hits

    for number, additions in grouped_terms.items():
        shard = load_shard(number)
        for term, hits in additions.items():
            # New-video ingestion is normally append-only.  Still remove any
            # old copy for an id being refreshed before merging its paragraphs.
            prior = [hit for hit in shard.get(term, []) if hit[0] not in video_ids]
            shard[term] = merge_hits(hits, prior)
        atomic_json_gzip_write(SHARDS / f"{number:03d}.json.gz", shard)

    rebuild_catalog()
    refresh_manifest()
    return len(touched_shards)
