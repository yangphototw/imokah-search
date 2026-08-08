"""Create a committed, hash-based completion ledger for every channel video.

This is the fast source of truth for scheduled updates.  It records whether a
catalog video has source transcript evidence, searchable hits, paragraph
context, and approved summaries.  A future run can compare hashes instead of
blindly rebuilding the entire channel.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from build_public_paragraph_index import OUTPUT as PARAGRAPH_INDEX, shard_id_for_video

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "catalog.json"
RAG = ROOT / "data" / "oka_rag_index.json"
TRANSCRIPTS = ROOT / "data" / "transcripts"
SEARCH_INDEX = PUBLIC / "search-index"
OUTPUT = ROOT / "data" / "processing_manifest.json"


def canonical_hash(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def catalog_videos() -> dict[str, dict]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {
        video["id"]: video
        for category in catalog["categories"]
        for video in category["videos"]
    }


def source_hashes() -> dict[str, tuple[str, str]]:
    """Prefer standalone current transcripts, otherwise fingerprint RAG cuts."""
    hashes = {}
    for path in TRANSCRIPTS.glob("*_transcript.json"):
        video_id = path.name.removesuffix("_transcript.json")
        chunks = json.loads(path.read_text(encoding="utf-8"))
        # Empty placeholder files and one-word failed recognitions are not
        # transcript evidence.  Mark them missing so the next update retries
        # them instead of treating a filename as completion.
        spoken_characters = sum(len(str(chunk.get("text", "")).strip()) for chunk in chunks)
        if spoken_characters >= 40:
            hashes[video_id] = (canonical_hash(chunks), "transcript")
    if not RAG.exists():
        return hashes
    grouped: dict[str, list[dict]] = defaultdict(list)
    for chunk in json.loads(RAG.read_text(encoding="utf-8")):
        video_id = str(chunk.get("video_id", ""))
        if video_id and video_id not in hashes:
            grouped[video_id].append({
                "start": chunk.get("start", 0),
                "timestamp": chunk.get("timestamp", ""),
                "text": chunk.get("text", ""),
            })
    for video_id, chunks in grouped.items():
        hashes[video_id] = (canonical_hash(chunks), "rag")
    return hashes


def paragraph_records() -> dict[str, list[dict]]:
    records = {}
    for path in PARAGRAPH_INDEX.glob("*.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            records.update(json.load(handle))
    return records


def searchable_ids() -> set[str]:
    ids = set()
    for path in SEARCH_INDEX.glob("*.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for hits in json.load(handle).values():
                ids.update(str(hit[0]) for hit in hits if hit)
    return ids


def build() -> dict:
    videos = catalog_videos()
    sources = source_hashes()
    paragraphs = paragraph_records()
    searchable = searchable_ids()
    records = {}
    for video_id, video in sorted(videos.items()):
        source_hash, source_kind = sources.get(video_id, ("", "missing"))
        paragraph_entries = paragraphs.get(video_id, [])
        paragraph_hash = canonical_hash(paragraph_entries) if paragraph_entries else ""
        approved = sum(1 for entry in paragraph_entries if entry.get("summary"))
        complete = bool(source_hash and video_id in searchable and paragraph_entries)
        records[video_id] = {
            "title_hash": canonical_hash(video.get("title", "")),
            "source_hash": source_hash,
            "source_kind": source_kind,
            "search_indexed": video_id in searchable,
            "paragraph_hash": paragraph_hash,
            "paragraphs": len(paragraph_entries),
            "approved_summaries": approved,
            "status": "complete" if complete else "incomplete",
        }
    return {
        "version": 1,
        "videos": records,
        "counts": {
            "catalog": len(videos),
            "complete": sum(record["status"] == "complete" for record in records.values()),
            "missing_source": sum(not record["source_hash"] for record in records.values()),
            "missing_search": sum(not record["search_indexed"] for record in records.values()),
            "missing_paragraphs": sum(not record["paragraphs"] for record in records.values()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail unless every catalog video is complete")
    args = parser.parse_args()
    manifest = build()
    if not args.check:
        OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    if args.check and manifest["counts"]["complete"] != manifest["counts"]["catalog"]:
        raise SystemExit("processing manifest reports incomplete catalog videos")


if __name__ == "__main__":
    main()
