"""Build compact, lazy-loaded paragraph context for the static search UI.

The search index deliberately stores tiny ASR cuts because it must be fast to
query.  Those cuts are evidence for *where* a query matched, not text that is
safe to show on its own.  This builder groups adjacent cuts into readable
paragraphs and publishes them in video-id shards.  The browser downloads a
paragraph shard only after a result has been found.

Optional approved summaries live in data/approved_paragraph_summaries.json.
They are intentionally separate from ASR and must have status="approved";
unreviewed model output is never published as a summary.
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from build_static_search_index import SHARD_COUNT
from paragraph_segmentation import paragraphize

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
RAG_INDEX = ROOT / "data" / "oka_rag_index.json"
TRANSCRIPTS = ROOT / "data" / "transcripts"
APPROVED_SUMMARIES = ROOT / "data" / "approved_paragraph_summaries.json"
OUTPUT = PUBLIC / "paragraph-index"


def shard_id_for_video(video_id: str) -> int:
    """FNV-1a; keep in sync with public/app.js."""
    value = 0x811C9DC5
    for character in video_id:
        value ^= ord(character)
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value & (SHARD_COUNT - 1)


def load_approved_summaries() -> dict[str, str]:
    if not APPROVED_SUMMARIES.exists():
        return {}
    payload = json.loads(APPROVED_SUMMARIES.read_text(encoding="utf-8"))
    records = payload.get("paragraphs", payload)
    approved = {}
    for paragraph_id, record in records.items():
        if isinstance(record, dict) and record.get("status") == "approved":
            summary = str(record.get("summary", "")).strip()
            if len(summary) >= 12:
                approved[paragraph_id] = summary
    return approved


def atomic_gzip_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as archive:
                archive.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def public_paragraphs(video_id: str, chunks: list[dict], approved: dict[str, str]) -> list[dict]:
    """Return readable display paragraphs, folding orphan tail cuts backward."""
    entries: list[dict] = []
    for paragraph in paragraphize(chunks):
        transcript = paragraph.raw_text
        # A final ASR tail can be only one or two words.  It has no value as a
        # standalone card, so fold it into the preceding bounded paragraph.
        if len(transcript) < 24 and entries:
            entries[-1]["end"] = round(paragraph.end, 2)
            entries[-1]["transcript"] += transcript
            continue
        entries.append({
            "id": "",  # Stable ids are assigned after any tail merge.
            "start": round(paragraph.start, 2),
            "end": round(paragraph.end, 2),
            "transcript": transcript,
        })
    if len(entries) >= 2 and len(entries[0]["transcript"]) < 24:
        first = entries.pop(0)
        entries[0]["start"] = first["start"]
        entries[0]["transcript"] = first["transcript"] + entries[0]["transcript"]
    if len(entries) == 1 and len(entries[0]["transcript"]) < 24:
        # Do not publish a lone fragment as if it were a readable paragraph.
        return []
    output = []
    for position, entry in enumerate(entries):
        paragraph_id = f"{video_id}:{position}"
        entry["id"] = paragraph_id
        if paragraph_id in approved:
            entry["summary"] = approved[paragraph_id]
        output.append(entry)
    return output


def prefer_current_transcripts(by_video: dict[str, list[dict]], transcript_dir: Path = TRANSCRIPTS) -> None:
    """Replace historical RAG chunks with the current local transcript source.

    The RAG corpus is useful as a fallback for archived material, but a full
    rebuild must never silently discard later transcript corrections merely
    because the same video id already exists in that corpus.
    """
    for transcript_path in transcript_dir.glob("*_transcript.json"):
        video_id = transcript_path.name.removesuffix("_transcript.json")
        transcript_chunks = json.loads(transcript_path.read_text(encoding="utf-8"))
        if transcript_chunks:
            by_video[video_id] = transcript_chunks


def build() -> tuple[int, int]:
    chunks = json.loads(RAG_INDEX.read_text(encoding="utf-8"))
    by_video: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        video_id = str(chunk.get("video_id", ""))
        if video_id:
            by_video[video_id].append(chunk)
    # Local transcripts are the current source of truth.  This replacement
    # preserves post-RAG corrections during a full rebuild; the historical
    # RAG corpus remains only as a fallback when a local transcript is absent.
    prefer_current_transcripts(by_video)

    approved = load_approved_summaries()
    shards: dict[int, dict[str, list[dict]]] = defaultdict(dict)
    paragraph_count = 0
    summary_count = 0
    for video_id, video_chunks in by_video.items():
        entries = public_paragraphs(video_id, video_chunks, approved)
        summary_count += sum(1 for entry in entries if entry.get("summary"))
        paragraph_count += len(entries)
        shards[shard_id_for_video(video_id)][video_id] = entries

    for number in range(SHARD_COUNT):
        atomic_gzip_json(OUTPUT / f"{number:03d}.json.gz", shards.get(number, {}))

    manifest = {
        "version": 1,
        "shards": SHARD_COUNT,
        "paragraphs": paragraph_count,
        "approved_summaries": summary_count,
        "schema": "video-id -> [{id,start,end,transcript,summary?}]",
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return paragraph_count, summary_count


def update_for_videos(video_ids: list[str]) -> int:
    """Refresh only video shards changed by the scheduled local updater."""
    if not video_ids:
        return 0
    approved = load_approved_summaries()
    changed_shards: set[int] = set()
    for video_id in video_ids:
        transcript_path = ROOT / "data" / "transcripts" / f"{video_id}_transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript missing for paragraph index: {transcript_path}")
        chunks = json.loads(transcript_path.read_text(encoding="utf-8"))
        number = shard_id_for_video(video_id)
        output_path = OUTPUT / f"{number:03d}.json.gz"
        if output_path.exists():
            with gzip.open(output_path, "rt", encoding="utf-8") as handle:
                shard = json.load(handle)
        else:
            shard = {}
        entries = public_paragraphs(video_id, chunks, approved)
        shard[video_id] = entries
        atomic_gzip_json(output_path, shard)
        changed_shards.add(number)

    # Keep counts accurate without re-reading the raw 430 MiB corpus.
    paragraphs = 0
    summaries = 0
    for output_path in OUTPUT.glob("*.json.gz"):
        with gzip.open(output_path, "rt", encoding="utf-8") as handle:
            shard = json.load(handle)
        for entries in shard.values():
            paragraphs += len(entries)
            summaries += sum(1 for entry in entries if entry.get("summary"))
    (OUTPUT / "manifest.json").write_text(json.dumps({
        "version": 1,
        "shards": SHARD_COUNT,
        "paragraphs": paragraphs,
        "approved_summaries": summaries,
        "schema": "video-id -> [{id,start,end,transcript,summary?}]",
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(changed_shards)


if __name__ == "__main__":
    paragraphs, summaries = build()
    print(f"Built {paragraphs:,} public paragraphs; {summaries:,} approved summaries.")
