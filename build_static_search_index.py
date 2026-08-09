"""Build the CDN-friendly paragraph search index used by the static site.

The public paragraph index is the single published transcript source of truth.
This builder deliberately indexes those paragraphs directly instead of looking
up offsets in the old, separately persisted RAG inverted index.  The old
scheme could become stale after a transcript rebuild and point a keyword at a
different video's sentence.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
SHARD_DIR = PUBLIC / "search-index"
PARAGRAPH_DIR = PUBLIC / "paragraph-index"
NEXT_SHARD_DIR = PUBLIC / ".search-index-next"
BACKUP_SHARD_DIR = PUBLIC / ".search-index-backup"
SHARD_COUNT = 512
MAX_HITS_PER_TERM = 12
MAX_HITS_PER_VIDEO_PER_TERM = 2
MAX_SHARD_BYTES = 1 * 1024 * 1024
MAX_TOTAL_INDEX_BYTES = 100 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]{1,4}")


def shard_id(term: str) -> int:
    """FNV-1a over UTF-16 code units; keep in sync with public/app.js."""
    value = 0x811C9DC5
    for char in term:
        code_point = ord(char)
        units = (code_point,) if code_point <= 0xFFFF else (
            0xD800 + ((code_point - 0x10000) >> 10),
            0xDC00 + ((code_point - 0x10000) & 0x3FF),
        )
        for unit in units:
            value ^= unit
            value = (value * 0x01000193) & 0xFFFFFFFF
    return value & (SHARD_COUNT - 1)


def paragraph_index_fingerprint() -> str:
    """Hash every published paragraph asset to make stale search builds fail QA."""
    files = [PARAGRAPH_DIR / "manifest.json", *sorted(PARAGRAPH_DIR.glob("*.json.gz"))]
    if len(files) != SHARD_COUNT + 1 or not files[0].exists():
        raise FileNotFoundError("Paragraph index is incomplete; run build_public_paragraph_index.py first")
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def tokens_for_text(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(str(text or "").lower()))


def format_timestamp(start: float) -> str:
    seconds = max(0, int(float(start or 0)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def iter_published_paragraphs():
    for path in sorted(PARAGRAPH_DIR.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            shard = json.load(handle)
        for video_id, paragraphs in shard.items():
            for paragraph in paragraphs:
                yield video_id, paragraph


def append_hit(bucket: dict[str, list[list]], term: str, hit: list) -> None:
    hits = bucket.setdefault(term, [])
    if len(hits) >= MAX_HITS_PER_TERM:
        return
    video_id = hit[0]
    if sum(existing[0] == video_id for existing in hits) >= MAX_HITS_PER_VIDEO_PER_TERM:
        return
    hits.append(hit)


def write_json_gzip(path: Path, value: dict) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as archive:
            archive.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def prepare_output_directory() -> None:
    """Recover from an interrupted earlier build, then create a clean staging area."""
    if not SHARD_DIR.exists() and BACKUP_SHARD_DIR.exists():
        BACKUP_SHARD_DIR.rename(SHARD_DIR)
    elif SHARD_DIR.exists() and BACKUP_SHARD_DIR.exists():
        shutil.rmtree(BACKUP_SHARD_DIR)
    if NEXT_SHARD_DIR.exists():
        shutil.rmtree(NEXT_SHARD_DIR)
    NEXT_SHARD_DIR.mkdir(parents=True)


def activate_output() -> None:
    """Swap a complete build in only after every shard has been written."""
    if BACKUP_SHARD_DIR.exists():
        shutil.rmtree(BACKUP_SHARD_DIR)
    if SHARD_DIR.exists():
        SHARD_DIR.rename(BACKUP_SHARD_DIR)
    try:
        NEXT_SHARD_DIR.rename(SHARD_DIR)
    except Exception:
        if not SHARD_DIR.exists() and BACKUP_SHARD_DIR.exists():
            BACKUP_SHARD_DIR.rename(SHARD_DIR)
        raise
    else:
        if BACKUP_SHARD_DIR.exists():
            shutil.rmtree(BACKUP_SHARD_DIR)


def main() -> None:
    if SHARD_COUNT <= 0 or SHARD_COUNT & (SHARD_COUNT - 1):
        raise SystemExit("SHARD_COUNT must be a positive power of two")

    source_fingerprint = paragraph_index_fingerprint()
    print("Building search terms from published paragraph context…", flush=True)
    buckets: list[dict[str, list[list]]] = [dict() for _ in range(SHARD_COUNT)]
    paragraphs = 0
    for video_id, paragraph in iter_published_paragraphs():
        text = str(paragraph.get("transcript", ""))
        start = float(paragraph.get("start", 0) or 0)
        # The searchable paragraph itself is fetched only after a match.  Do
        # not repeat it under every term here: that would multiply static CDN
        # size and mobile memory use by hundreds of megabytes.
        hit = [video_id, format_timestamp(start), "", start]
        for term in tokens_for_text(text):
            append_hit(buckets[shard_id(term)], term, hit)
        paragraphs += 1

    prepare_output_directory()
    print(f"Writing {SHARD_COUNT} compressed shards…", flush=True)
    manifest = {
        "version": 3,
        "shards": SHARD_COUNT,
        "terms": 0,
        "paragraphs": paragraphs,
        "max_hits_per_term": MAX_HITS_PER_TERM,
        "max_hits_per_video_per_term": MAX_HITS_PER_VIDEO_PER_TERM,
        "source": "paragraph-index",
        "paragraph_index_sha256": source_fingerprint,
        "files": {},
    }
    for number, bucket in enumerate(buckets):
        filename = f"{number:03d}.json.gz"
        write_json_gzip(NEXT_SHARD_DIR / filename, bucket)
        manifest["terms"] += len(bucket)
        manifest["files"][filename] = len(bucket)
        buckets[number] = None
    with (NEXT_SHARD_DIR / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, separators=(",", ":"))

    total_size = sum(path.stat().st_size for path in NEXT_SHARD_DIR.glob("*.json.gz"))
    activate_output()
    print(
        f"Done: {manifest['terms']:,} terms from {paragraphs:,} paragraphs, "
        f"{total_size / 1024 / 1024:.1f} MiB compressed",
        flush=True,
    )


if __name__ == "__main__":
    main()
