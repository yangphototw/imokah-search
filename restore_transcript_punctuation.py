"""Restore display punctuation without changing transcript words.

The transcript corpus is evidence.  This tool treats a punctuation model as a
display-only formatter: its output is accepted only when its non-punctuation
characters match the source, and the final text is reconstructed from the
source characters.  That prevents accidental changes such as ``OK`` becoming
``Ok`` from reaching the website.

Accepted output is stored in an ignored, resumable ledger.  The public index
builder verifies both the source hash and the punctuation-only constraint
again before it uses a ledger entry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_cache import configure_project_cache


ROOT = Path(__file__).resolve().parent
configure_project_cache()

DEFAULT_MODEL = "funasr/ct-punc"
DEFAULT_HUB = "hf"
LEDGER_PATH = ROOT / "data" / "transcript_punctuation_ledger.json"
SUPPORTED_MODEL_PUNCTUATION = frozenset("，。！？；：、,.!?;:")
PUNCTUATION_DISPLAY_FORM = {
    ",": "，",
    ".": "。",
    "!": "！",
    "?": "？",
    ";": "；",
    ":": "：",
}


def is_punctuation(character: str) -> bool:
    return unicodedata.category(character).startswith("P")


def source_sha256(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def meaningful_characters(text: str) -> list[str]:
    """Return spoken characters, excluding whitespace and punctuation."""
    return [
        character
        for character in str(text or "")
        if not character.isspace() and not is_punctuation(character)
    ]


def candidate_punctuation_by_boundary(raw_text: str, candidate_text: str) -> dict[int, str] | None:
    """Map model punctuation to boundaries after source content characters.

    Case-insensitive comparison is intentional *only* for alignment.  The
    caller always rebuilds the visible text from ``raw_text``, preserving its
    original letter case and every non-punctuation character exactly.
    """
    raw_characters = meaningful_characters(raw_text)
    candidate_characters = meaningful_characters(candidate_text)
    if not candidate_text or len(raw_characters) != len(candidate_characters):
        return None
    if [character.casefold() for character in raw_characters] != [character.casefold() for character in candidate_characters]:
        return None

    punctuation: dict[int, list[str]] = {}
    boundary = 0
    for character in candidate_text:
        if character.isspace():
            continue
        if is_punctuation(character):
            if character in SUPPORTED_MODEL_PUNCTUATION:
                punctuation.setdefault(boundary, []).append(PUNCTUATION_DISPLAY_FORM.get(character, character))
            continue
        boundary += 1

    if boundary != len(raw_characters):
        return None
    return {position: "".join(characters) for position, characters in punctuation.items()}


def punctuate_text(raw_text: str, candidate_text: str) -> str | None:
    """Return source text with accepted model punctuation, or ``None``.

    Existing source punctuation is never moved or replaced.  A model mark is
    inserted only into a source boundary that currently contains no punctuation.
    """
    raw_text = str(raw_text or "")
    punctuation = candidate_punctuation_by_boundary(raw_text, str(candidate_text or ""))
    if punctuation is None:
        return None

    output: list[str] = []
    position = 0
    index = 0
    while index < len(raw_text):
        character = raw_text[index]
        if character.isspace() or is_punctuation(character):
            output.append(character)
            index += 1
            continue

        position += 1
        output.append(character)
        tail_start = index + 1
        tail_end = tail_start
        while tail_end < len(raw_text):
            next_character = raw_text[tail_end]
            if not next_character.isspace() and not is_punctuation(next_character):
                break
            tail_end += 1
        tail = raw_text[tail_start:tail_end]
        if position in punctuation and not any(is_punctuation(item) for item in tail):
            output.append(punctuation[position])
        output.append(tail)
        index = tail_end

    # Prefix punctuation belongs to the source and is already preserved.  A
    # model-generated prefix mark is deliberately ignored: it has no spoken
    # anchor and is rarely useful in transcript display.
    return "".join(output)


def is_punctuation_only_change(raw_text: str, candidate_text: str) -> bool:
    return punctuate_text(raw_text, candidate_text) is not None


def load_punctuation_model(model_name: str = DEFAULT_MODEL, hub: str = DEFAULT_HUB) -> Any:
    """Load the local model once for a whole resumable ledger run."""
    from funasr import AutoModel

    return AutoModel(model=model_name, hub=hub, disable_update=True, device="cpu")


def restore_texts(
    texts: Iterable[str],
    model_name: str = DEFAULT_MODEL,
    hub: str = DEFAULT_HUB,
    batch_size_seconds: int = 300,
    model: Any | None = None,
) -> list[dict[str, str | bool]]:
    """Punctuate one batch locally and return only source-preserving output."""
    raw_texts = [str(text or "").strip() for text in texts]
    results: list[dict[str, str | bool] | None] = [None] * len(raw_texts)
    nonempty_indices = [index for index, text in enumerate(raw_texts) if text]
    for index, raw_text in enumerate(raw_texts):
        if not raw_text:
            results[index] = {"raw_text": raw_text, "display_text": raw_text, "accepted": True, "model_output": raw_text}
    if not nonempty_indices:
        return [result for result in results if result is not None]

    model = model or load_punctuation_model(model_name, hub)
    generated_results = model.generate(
        input=[raw_texts[index] for index in nonempty_indices],
        batch_size_s=batch_size_seconds,
    )
    if len(generated_results) != len(nonempty_indices):
        raise RuntimeError(f"Punctuation model returned {len(generated_results)} results for {len(nonempty_indices)} inputs")
    for index, generated in zip(nonempty_indices, generated_results, strict=True):
        raw_text = raw_texts[index]
        model_output = str(generated.get("text", "")) if isinstance(generated, dict) else ""
        display_text = punctuate_text(raw_text, model_output)
        results[index] = {
            "raw_text": raw_text,
            "display_text": display_text if display_text is not None else raw_text,
            "accepted": display_text is not None,
            "model_output": model_output,
        }
    return [result for result in results if result is not None]


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 2, "publication_status": "draft", "records": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("records", {}), dict):
        raise ValueError(f"Invalid punctuation ledger: {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def current_paragraphs() -> list[dict[str, str]]:
    """Return stable, pre-punctuation paragraphs used by the public builder."""
    from build_public_paragraph_index import load_source_videos, public_paragraphs

    paragraphs: list[dict[str, str]] = []
    for video_id, chunks in load_source_videos().items():
        paragraphs.extend(public_paragraphs(video_id, chunks, approved={}))
    return paragraphs


def record_is_current(record: Any, raw_text: str) -> bool:
    return (
        isinstance(record, dict)
        and record.get("status") in {"accepted", "rejected_content_change"}
        and record.get("source_sha256") == source_sha256(raw_text)
        and record.get("source_text") == raw_text
    )


def build_ledger(
    limit: int | None = None,
    sample: bool = False,
    batch_size: int = 32,
    batch_size_seconds: int = 300,
    ledger_path: Path = LEDGER_PATH,
    model_name: str = DEFAULT_MODEL,
    hub: str = DEFAULT_HUB,
) -> dict[str, int]:
    """Resume punctuation formatting for stable paragraphs and atomically save it."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    ledger = load_ledger(ledger_path)
    records = ledger.setdefault("records", {})
    pending = [
        paragraph
        for paragraph in current_paragraphs()
        if not record_is_current(records.get(paragraph["id"]), paragraph["transcript"])
    ]
    if sample:
        # A stable hash provides cross-channel coverage without introducing a
        # random seed that would make later audit reproduction difficult.
        pending.sort(key=lambda paragraph: source_sha256(paragraph["id"]))
    if limit is not None:
        pending = pending[:limit]

    accepted = rejected = 0
    model = load_punctuation_model(model_name, hub) if pending else None
    for offset in range(0, len(pending), batch_size):
        batch = pending[offset:offset + batch_size]
        restored = restore_texts(
            [paragraph["transcript"] for paragraph in batch],
            model_name=model_name,
            hub=hub,
            batch_size_seconds=batch_size_seconds,
            model=model,
        )
        for paragraph, result in zip(batch, restored, strict=True):
            status = "accepted" if result["accepted"] else "rejected_content_change"
            accepted += int(bool(result["accepted"]))
            rejected += int(not bool(result["accepted"]))
            records[paragraph["id"]] = {
                "status": status,
                "source_sha256": source_sha256(paragraph["transcript"]),
                "source_text": paragraph["transcript"],
                "display_text": result["display_text"],
                "model_output": result["model_output"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ledger.update({
            "schema_version": 2,
            # New or reprocessed display text always needs another complete
            # audit before it can be served by the static site.
            "publication_status": "draft",
            "provider": {"model": model_name, "hub": hub},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        write_json_atomic(ledger_path, ledger)

    return {"pending": len(pending), "accepted": accepted, "rejected": rejected, "total_records": len(records)}


def approve_ledger_for_publication(
    ledger_path: Path = LEDGER_PATH,
    approval_note: str = "",
) -> dict[str, int]:
    """Mark a *complete* locally reviewed ledger safe for static publishing.

    This deliberately cannot approve a partial run.  It is a final explicit
    gate after the human quality review, not an automatic model decision.
    """
    approval_note = approval_note.strip()
    if not approval_note:
        raise ValueError("An approval note is required for publication")
    ledger = load_ledger(ledger_path)
    records = ledger["records"]
    missing_or_stale = []
    rejected = []
    paragraphs = current_paragraphs()
    for paragraph in paragraphs:
        record = records.get(paragraph["id"])
        if not record_is_current(record, paragraph["transcript"]):
            missing_or_stale.append(paragraph["id"])
        elif record.get("status") != "accepted":
            rejected.append(paragraph["id"])
    if missing_or_stale or rejected:
        raise RuntimeError(
            "Ledger is not ready for publication: "
            f"{len(missing_or_stale)} missing/stale, {len(rejected)} rejected"
        )
    ledger.update({
        "schema_version": 2,
        "publication_status": "approved",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approval_note": approval_note,
    })
    write_json_atomic(ledger_path, ledger)
    return {"paragraphs": len(paragraphs), "approved": len(records)}


def main() -> None:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--probe", action="store_true", help="Run two representative paragraphs locally.")
    actions.add_argument("--build-ledger", action="store_true", help="Resume the local punctuation ledger.")
    actions.add_argument("--approve-for-publication", action="store_true", help="Approve a complete, human-reviewed ledger for static publishing.")
    parser.add_argument("--limit", type=int, help="Maximum pending paragraphs to process.")
    parser.add_argument("--sample", action="store_true", help="Choose pending paragraphs by stable cross-channel sample order.")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--batch-size-seconds", type=int, default=300)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--hub", default=DEFAULT_HUB)
    parser.add_argument("--approval-note", help="Required audit note when approving publication.")
    args = parser.parse_args()

    if args.probe:
        samples = [
            "OK大家好我是道慈我們今天要分享富士新推出的X100VI這台相機",
            "在文廟拍攝時我們先觀察光線再決定要不要提高ISO",
        ]
        for result in restore_texts(samples, args.model, args.hub, args.batch_size_seconds):
            print(f"accepted={result['accepted']}")
            print(result["display_text"])
        return

    if args.approve_for_publication:
        print(json.dumps(
            approve_ledger_for_publication(approval_note=args.approval_note or ""),
            ensure_ascii=False,
        ))
        return

    statistics = build_ledger(
        limit=args.limit,
        sample=args.sample,
        batch_size=args.batch_size,
        batch_size_seconds=args.batch_size_seconds,
        model_name=args.model,
        hub=args.hub,
    )
    print(json.dumps(statistics, ensure_ascii=False))


if __name__ == "__main__":
    main()
