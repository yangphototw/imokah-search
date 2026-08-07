"""Validate local ASR reviews and classify proposed transcript corrections."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REVIEWS = ROOT / "data" / "transcript_audio_reviews.json"
OUTPUT = ROOT / "data" / "transcript_review_evaluation.json"
REQUIRED_FIELDS = {
    "schema_version", "reviewed_at", "video_id", "start", "end", "audio_path",
    "clip_start", "clip_end", "raw_text", "candidate_text", "flags", "asr",
}


def correction_targets(flags: list[str]) -> list[str]:
    return [flag.rsplit(" → ", 1)[1] for flag in flags if " → " in flag]


def classify(review: dict, model_names: list[str]) -> dict:
    missing_fields = sorted(REQUIRED_FIELDS - review.keys())
    missing_models = [name for name in model_names if not review.get("asr", {}).get(name)]
    targets = correction_targets(review.get("flags", []))
    host_identity = any(
        flag.startswith(("name in ", "channel host honorific"))
        for flag in review.get("flags", [])
    )
    model_support = {
        target: [name for name in model_names if target in review.get("asr", {}).get(name, "")]
        for target in targets
    }

    if missing_fields or missing_models:
        status = "incomplete"
        recommendation = "run_missing_models"
    elif host_identity:
        status = "channel_identity_supported"
        recommendation = "accept_candidate_with_channel_identity_provenance"
    elif targets and all(len(model_support[target]) == len(model_names) for target in targets):
        status = "all_models_support_candidate"
        recommendation = "accept_candidate"
    elif targets:
        status = "ambiguous"
        recommendation = "editorial_review_required"
    else:
        status = "no_automatic_correction"
        recommendation = "keep_raw_text"

    return {
        "status": status,
        "recommendation": recommendation,
        "missing_fields": missing_fields,
        "missing_models": missing_models,
        "correction_targets": targets,
        "model_support": model_support,
    }


def evaluate(reviews: dict[str, dict], model_names: list[str]) -> dict:
    decisions = {review_id: classify(review, model_names) for review_id, review in reviews.items()}
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models_required": model_names,
        "summary": dict(sorted(Counter(value["status"] for value in decisions.values()).items())),
        "decisions": decisions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="small,medium,large-v3")
    parser.add_argument("--write", action="store_true", help="Write the full local decision file.")
    args = parser.parse_args()
    model_names = [name.strip() for name in args.models.split(",") if name.strip()]
    if not model_names:
        parser.error("--models must contain at least one model name")
    if not REVIEWS.exists():
        parser.error(f"Review file not found: {REVIEWS}. Run review_audio_paragraphs.py first.")

    report = evaluate(json.loads(REVIEWS.read_text(encoding="utf-8")), model_names)
    if args.write:
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {OUTPUT}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
