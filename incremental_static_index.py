"""Update only the CDN search shards touched by newly transcribed videos."""

import gzip
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from build_static_search_index import MAX_HITS_PER_TERM, PUBLIC, SHARD_COUNT, shard_id

ROOT = Path(__file__).resolve().parent
TRANSCRIPTS = ROOT / "data" / "transcripts"
SHARDS = PUBLIC / "search-index"
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


def tokens_for_chunk(chunk: dict) -> set[str]:
    content = f"{chunk.get('text', '')} {chunk.get('video_title', '')}".lower()
    return set(TOKEN_PATTERN.findall(content))


def load_shard(number: int) -> dict:
    path = SHARDS / f"{number:03d}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def build_video_hits(video_ids: list[str]) -> tuple[dict[str, list[list]], set[int]]:
    term_hits: dict[str, list[list]] = defaultdict(list)
    touched_shards: set[int] = set()

    for video_id in video_ids:
        transcript = TRANSCRIPTS / f"{video_id}_transcript.json"
        if not transcript.exists():
            raise FileNotFoundError(f"Transcript missing for {video_id}: {transcript}")
        chunks = json.loads(transcript.read_text(encoding="utf-8"))
        for chunk in chunks:
            hit = [
                chunk.get("video_id", video_id),
                chunk.get("timestamp", "00:00"),
                chunk.get("text", ""),
                chunk.get("start", 0),
            ]
            for term in tokens_for_chunk(chunk):
                term_hits[term].append(hit)
                touched_shards.add(shard_id(term))
    return term_hits, touched_shards


def merge_hits(new_hits: list[list], existing_hits: list[list]) -> list[list]:
    """Prefer fresh clips, remove duplicates, and preserve the CDN size budget."""
    merged = []
    seen = set()
    for hit in new_hits + existing_hits:
        key = (hit[0], hit[1])
        if key not in seen:
            seen.add(key)
            merged.append(hit)
            if len(merged) == MAX_HITS_PER_TERM:
                break
    return merged


def rebuild_catalog() -> None:
    # Import lazily so a static-site-only workflow does not load legacy search
    # data until this small catalog has to be regenerated.
    from web_server import build_encyclopedia_data

    atomic_json_write(CATALOG, build_encyclopedia_data())


def refresh_manifest() -> None:
    file_counts = {}
    total_terms = 0
    for number in range(SHARD_COUNT):
        shard = load_shard(number)
        filename = f"{number:03d}.json.gz"
        file_counts[filename] = len(shard)
        total_terms += len(shard)
    manifest = {
        "version": 2,
        "shards": SHARD_COUNT,
        "terms": total_terms,
        "max_hits_per_term": MAX_HITS_PER_TERM,
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
            shard[term] = merge_hits(hits, shard.get(term, []))
        atomic_json_gzip_write(SHARDS / f"{number:03d}.json.gz", shard)

    rebuild_catalog()
    refresh_manifest()
    return len(touched_shards)
