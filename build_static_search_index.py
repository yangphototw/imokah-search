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
SOURCE = ROOT / "data" / "oka_search_db.json.gz"
PUBLIC = ROOT / "public"
SHARD_DIR = PUBLIC / "search-index"
NEXT_SHARD_DIR = PUBLIC / ".search-index-next"
BACKUP_SHARD_DIR = PUBLIC / ".search-index-backup"
NEXT_CATALOG = PUBLIC / ".catalog.next.json"
SHARD_COUNT = 512


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
    if not SOURCE.exists():
        raise SystemExit(f"Missing source index: {SOURCE}")

    if SHARD_COUNT <= 0 or SHARD_COUNT & (SHARD_COUNT - 1):
        raise SystemExit("SHARD_COUNT must be a positive power of two")

    prepare_output_directory()
    print("Loading compressed search index…", flush=True)
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        search_db = json.load(handle)

    buckets = [{} for _ in range(SHARD_COUNT)]
    while search_db:
        term, hits = search_db.popitem()
        normalized_term = term.lower()
        bucket = buckets[shard_id(normalized_term)]
        # The server lookup is case-insensitive.  Preserve every hit when the
        # source contains multiple case variants of the same search term.
        if normalized_term in bucket:
            bucket[normalized_term].extend(hits)
        else:
            bucket[normalized_term] = hits

    print(f"Writing {SHARD_COUNT} compressed shards…", flush=True)
    manifest = {"version": 1, "shards": SHARD_COUNT, "terms": 0, "files": {}}
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
