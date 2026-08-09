"""Deterministic quality gate for the Markdown knowledge base."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KNOWLEDGE = ROOT / "knowledge"
CATALOG = ROOT / "public" / "catalog.json"
PROCESSING = ROOT / "data" / "processing_manifest.json"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    video_ids = {video["id"] for category in catalog["categories"] for video in category["videos"]}
    processing = json.loads(PROCESSING.read_text(encoding="utf-8"))
    if set(processing.get("videos", {})) != video_ids:
        fail("processing ledger and catalog have different video IDs")
    expected = {f"{video_id}.md" for video_id in video_ids}
    actual = {path.name for path in (KNOWLEDGE / "videos").glob("*.md")}
    if actual != expected:
        fail("knowledge/video pages do not cover exactly the catalog")
    for required in ("README.md", "INDEX.md", "ERRATA.md", "FACT_CHECK_QUEUE.md", "manifest.json"):
        if not (KNOWLEDGE / required).exists():
            fail(f"missing knowledge document: {required}")
    errata = (KNOWLEDGE / "ERRATA.md").read_text(encoding="utf-8")
    if "oka_ai_summaries.json" not in errata or "不可作為" not in errata:
        fail("legacy template summary exclusion is not documented")
    manifest = json.loads((KNOWLEDGE / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("videos") != len(video_ids) or manifest.get("passages", 0) <= 0:
        fail("knowledge manifest counts are invalid")
    print(f"PASS: {manifest['videos']} Markdown video pages; {manifest['passages']:,} evidence passages; {manifest['fact_check_candidates']:,} fact-check candidates")


if __name__ == "__main__":
    main()
