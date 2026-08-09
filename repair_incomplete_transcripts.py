"""Repair only videos marked incomplete by the committed processing ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_processing_manifest import build as build_processing_manifest
from build_public_paragraph_index import update_for_videos as update_paragraphs
from channel_update import make_transcriber, save_transcript, transcribe
from incremental_static_index import update_for_new_videos

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MANIFEST = DATA / "processing_manifest.json"
MAP = DATA / "oka_youtube_map.json"
CATALOG = ROOT / "public" / "catalog.json"


def videos_by_id() -> dict[str, dict]:
    videos = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog = {
        item["id"]: item
        for category in videos["categories"]
        for item in category["videos"]
    }
    source = json.loads(MAP.read_text(encoding="utf-8"))
    return {
        video_id: {
            "id": video_id,
            "title": source.get(video_id, {}).get("title") or item["title"],
            "url": item["url"],
        }
        for video_id, item in catalog.items()
    }


def write_manifest() -> dict:
    manifest = build_processing_manifest()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="medium", help="faster-whisper model size")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ids", nargs="*", help="Explicit video IDs; otherwise all incomplete entries")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = args.ids or [
        video_id for video_id, record in manifest["videos"].items()
        if record.get("status") == "incomplete"
    ]
    if args.limit:
        selected = selected[:args.limit]
    videos = videos_by_id()
    selected = [video_id for video_id in selected if video_id in videos]
    print(f"Repairing {len(selected)} incomplete videos with one {args.model} model instance.", flush=True)
    if not selected:
        return 0

    model, device = make_transcriber(args.model)
    print(f"Transcribing on {device}.", flush=True)
    completed = []
    for video_id in selected:
        try:
            chunks = transcribe(videos[video_id], model)
            save_transcript(videos[video_id], chunks)
            completed.append(video_id)
            print(f"OK {video_id}: {len(chunks)} segments", flush=True)
        except Exception as error:
            print(f"FAILED {video_id}: {error}", flush=True)

    if completed:
        search_shards = update_for_new_videos(completed)
        paragraph_shards = update_paragraphs(completed)
        print(f"Updated {search_shards} search shards and {paragraph_shards} paragraph shards.", flush=True)
    final = write_manifest()
    print(json.dumps(final["counts"], ensure_ascii=False), flush=True)
    return 0 if final["counts"]["covered"] == final["counts"]["catalog"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
