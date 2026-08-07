"""Build a local, reviewable paragraph audit from the existing ASR corpus."""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

from paragraph_segmentation import paragraphize

ROOT = Path(__file__).resolve().parent
RAG_INDEX = ROOT / "data" / "oka_rag_index.json"
OUTPUT = ROOT / "data" / "transcript_paragraph_audit.json.gz"


def main() -> None:
    chunks = json.loads(RAG_INDEX.read_text(encoding="utf-8"))
    by_video: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        video_id = chunk.get("video_id", "")
        if video_id:
            by_video[video_id].append(chunk)

    paragraphs = []
    flagged = 0
    for video_id, video_chunks in by_video.items():
        title = video_chunks[0].get("video_title", "")
        for index, paragraph in enumerate(paragraphize(video_chunks)):
            needs_audio_review = bool(paragraph.flags)
            flagged += needs_audio_review
            paragraphs.append({
                "id": f"{video_id}:{index}",
                "video_id": video_id,
                "title": title,
                "start": round(paragraph.start, 2),
                "end": round(paragraph.end, 2),
                "raw_text": paragraph.raw_text,
                "candidate_text": paragraph.corrected_text,
                "flags": paragraph.flags,
                "needs_audio_review": needs_audio_review,
            })

    payload = {"version": 1, "paragraphs": paragraphs}
    with gzip.open(OUTPUT, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    print(f"Built {len(paragraphs):,} paragraphs; {flagged:,} need audio review.")


if __name__ == "__main__":
    main()
