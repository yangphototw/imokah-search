"""Regression checks for strict, evidence-backed browser search results."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from build_public_paragraph_index import shard_id_for_video
from build_static_search_index import paragraph_index_fingerprint, shard_id

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
SEARCH = PUBLIC / "search-index"
PARAGRAPHS = PUBLIC / "paragraph-index"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_search_term(term: str) -> list[list]:
    with gzip.open(SEARCH / f"{shard_id(term):03d}.json.gz", "rt", encoding="utf-8") as handle:
        return json.load(handle).get(term, [])


def paragraph_text(video_id: str, start: float) -> str:
    path = PARAGRAPHS / f"{shard_id_for_video(video_id):03d}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        entries = json.load(handle).get(video_id, [])
    for entry in entries:
        if float(entry.get("start", -1)) == float(start):
            return str(entry.get("transcript", ""))
    fail(f"search hit has no matching paragraph: {video_id} at {start}")


def title_matches_groups(title: str, groups: list[list[str]]) -> bool:
    normalized = title.lower().replace(" ", "").replace("-", "").replace("_", "")
    return all(any(term.replace(" ", "").replace("-", "").replace("_", "") in normalized for term in group) for group in groups)


def main() -> None:
    manifest = json.loads((SEARCH / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("source") != "paragraph-index":
        fail("search index is not built from the published paragraph source")
    if manifest.get("paragraph_index_sha256") != paragraph_index_fingerprint():
        fail("search index is stale relative to the published paragraph source")

    # Every sampled hit must point to a paragraph that actually contains the
    # term.  This catches the historical stale-offset failure deterministically.
    for term in ("gr3", "街拍", "iso", "光圈"):
        hits = load_search_term(term)
        if not hits:
            fail(f"expected indexed term is missing: {term}")
        for video_id, _timestamp, _excerpt, start in hits:
            if term not in paragraph_text(video_id, start).lower():
                fail(f"{term!r} hit points to unrelated paragraph: {video_id} at {start}")

    catalog = json.loads((PUBLIC / "catalog.json").read_text(encoding="utf-8"))
    titles = [video["title"] for category in catalog["categories"] for video in category["videos"]]
    false_positive_titles = [
        title for title in titles
        if "加德滿都，街拍聖地" in title or "高速對焦與眼部追焦實測" in title
    ]
    if len(false_positive_titles) != 2:
        fail("known false-positive titles are no longer available for the regression check")
    gr3_street_groups = [["gr3", "griii", "gr iii", "gr 3"], ["街拍", "快照", "snap", "street photography", "掃街", "抓拍"]]
    if any(title_matches_groups(title, gr3_street_groups) for title in false_positive_titles):
        fail("a partial title still qualifies as a GR3 street-photography match")

    app = (PUBLIC / "app.js").read_text(encoding="utf-8")
    required = (
        "if (matchesAllTermGroups(title, termGroups))",
        ".filter(item => item.isTitleMatch || matchesAllTermGroups(item.transcript, termGroups))",
        "'接拍': '街拍'",
        "const KNOWN_QUERY_TERMS",
    )
    if any(fragment not in app for fragment in required):
        fail("browser search no longer enforces the relevance contract")

    print("PASS: title, paragraph, and source-fingerprint relevance checks")


if __name__ == "__main__":
    main()
