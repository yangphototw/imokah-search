"""Create a safe, auditable ledger of audio-supported transcript corrections.

The ledger is intentionally separate from raw ASR files.  Applying a proposed
replacement to source text is a later, hash-checked operation; this command
only records corrections backed by the review policy.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REVIEWS = ROOT / "data" / "transcript_audio_reviews.json"
EVALUATION = ROOT / "data" / "transcript_review_evaluation.json"
OUTPUT = ROOT / "data" / "transcript_correction_ledger.json"
ACCEPTED_STATUSES = {"all_models_support_candidate", "channel_identity_supported"}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_ledger(reviews: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    skipped = Counter()

    for review_id, decision in decisions.items():
        review = reviews.get(review_id)
        if not review:
            skipped["missing_review"] += 1
            continue
        status = str(decision.get("status", ""))
        if status not in ACCEPTED_STATUSES:
            skipped[status or "unknown_status"] += 1
            continue
        raw_text = str(review.get("raw_text", ""))
        candidate_text = str(review.get("candidate_text", ""))
        if not raw_text or raw_text == candidate_text:
            skipped["no_text_change"] += 1
            continue
        if decision.get("missing_fields") or decision.get("missing_models"):
            skipped["incomplete_evidence"] += 1
            continue

        records[review_id] = {
            "status": "accepted_pending_apply",
            "recommendation": decision.get("recommendation", ""),
            "reviewed_at": review.get("reviewed_at", ""),
            "video_id": review.get("video_id", ""),
            "start": review.get("start"),
            "end": review.get("end"),
            "raw_sha256": digest(raw_text),
            "candidate_sha256": digest(candidate_text),
            "raw_text": raw_text,
            "candidate_text": candidate_text,
            "flags": review.get("flags", []),
            "models": sorted(review.get("asr", {}).keys()),
        }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "summary": {
            "accepted_pending_apply": len(records),
            "skipped": dict(sorted(skipped.items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the audio-supported transcript correction ledger.")
    parser.add_argument("--write", action="store_true", help="Write data/transcript_correction_ledger.json.")
    args = parser.parse_args()
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))
    evaluation = json.loads(EVALUATION.read_text(encoding="utf-8"))
    ledger = build_ledger(reviews, evaluation.get("decisions", {}))
    if args.write:
        OUTPUT.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(json.dumps(ledger["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
