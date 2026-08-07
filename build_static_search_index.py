"""Build CDN-friendly static search shards for the browser-only search UI.

The generated .json.gz files are intentionally served as ordinary binary assets.
app.js decompresses only the few shards needed for a query, avoiding Vercel
Function memory and cold-start costs entirely.
"""

import gzip
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PUBLIC = ROOT / "public"
SHARD_DIR = PUBLIC / "search-index"
NEXT_SHARD_DIR = PUBLIC / ".search-index-next"
BACKUP_SHARD_DIR = PUBLIC / ".search-index-backup"
NEXT_CATALOG = PUBLIC / ".catalog.next.json"
SHARD_COUNT = 512
# A static site must bound both download size and client-side decompression.
# More than a dozen clips for one exact term provides little additional value
# because title matches and synonym expansion still contribute extra results.
MAX_HITS_PER_TERM = 12
# Deployment regression budgets.  Static assets should remain comfortably
# below free-hosting limits and cheap to decompress on a phone.
MAX_SHARD_BYTES = 1 * 1024 * 1024
MAX_TOTAL_INDEX_BYTES = 100 * 1024 * 1024


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


def write_json_gzip(path: Path, value) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))


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
    """Swap a complete build in only after every shard and catalog has been written."""
    if BACKUP_SHARD_DIR.exists():
        shutil.rmtree(BACKUP_SHARD_DIR)
    if SHARD_DIR.exists():
        SHARD_DIR.rename(BACKUP_SHARD_DIR)

    try:
        NEXT_SHARD_DIR.rename(SHARD_DIR)
        NEXT_CATALOG.replace(PUBLIC / "catalog.json")
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

    prepare_output_directory()
    rag_index_file = ROOT / "data" / "oka_rag_index.json"
    inverted_index_file = ROOT / "data" / "oka_inverted_index.json"
    if not rag_index_file.exists() or not inverted_index_file.exists():
        raise SystemExit("Missing RAG source files; rebuild the RAG and inverted indexes first")

    print("Loading RAG index and Inverted index…", flush=True)
    with rag_index_file.open("r", encoding="utf-8") as f:
        chunks = json.load(f)
    with inverted_index_file.open("r", encoding="utf-8") as f:
        inv_map = json.load(f)

    buckets = [{} for _ in range(SHARD_COUNT)]
    for term, indices in inv_map.items():
        normalized_term = term.lower()
        bucket = buckets[shard_id(normalized_term)]
        hits = []
        # The old builder copied every occurrence of a common word.  A single
        # term could therefore create a 10+ MiB shard and freeze a browser.
        for idx in indices[:MAX_HITS_PER_TERM]:
            c = chunks[idx]
            v_id = c.get('video_id') or c.get('source')
            hits.append([v_id, c.get('timestamp', '00:00'), c.get('text', ''), c.get('start', 0)])
        
        if normalized_term in bucket:
            bucket[normalized_term].extend(hits)
        else:
            bucket[normalized_term] = hits

    # Drop source containers before serialising so the output stage keeps the
    # lowest practical peak memory for an offline build.
    del inv_map
    del chunks

    print(f"Writing {SHARD_COUNT} compressed shards…", flush=True)
    manifest = {
        "version": 2,
        "shards": SHARD_COUNT,
        "terms": 0,
        "max_hits_per_term": MAX_HITS_PER_TERM,
        "files": {},
    }
    for number, bucket in enumerate(buckets):
        filename = f"{number:03d}.json.gz"
        write_json_gzip(NEXT_SHARD_DIR / filename, bucket)
        manifest["terms"] += len(bucket)
        manifest["files"][filename] = len(bucket)
        buckets[number] = None

    # Build the initial page's data once at build time rather than during a
    # request.  It lets Vercel cache catalog.json as a normal static asset.
    from web_server import build_encyclopedia_data
    with NEXT_CATALOG.open("w", encoding="utf-8") as handle:
        json.dump(build_encyclopedia_data(), handle, ensure_ascii=False, separators=(",", ":"))
    with (NEXT_SHARD_DIR / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, separators=(",", ":"))

    total_size = sum(path.stat().st_size for path in NEXT_SHARD_DIR.glob("*.json.gz"))
    activate_output()
    print(f"Done: {manifest['terms']:,} terms, {total_size / 1024 / 1024:.1f} MiB compressed", flush=True)


if __name__ == "__main__":
    main()
