"""Resumable local ASR review for paragraphs flagged by the audit."""

from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timezone
import gc
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from project_cache import configure_project_cache

configure_project_cache()
sys.path.insert(0, str(ROOT / ".python-packages"))
os.environ["PATH"] = os.pathsep.join([
    str(ROOT / ".python-packages" / "nvidia" / "cublas" / "bin"),
    str(ROOT / ".python-packages" / "nvidia" / "cudnn" / "bin"),
    str(ROOT / ".python-packages" / "nvidia" / "cuda_nvrtc" / "bin"),
    os.environ["PATH"],
])

from faster_whisper import WhisperModel
import faster_whisper.transcribe as faster_whisper_transcribe
from tqdm import tqdm

AUDIT = ROOT / "data" / "transcript_paragraph_audit.json.gz"
REVIEWS = ROOT / "data" / "transcript_audio_reviews.json"
AUDIO_ROOT = Path(r"F:\AI_Youtube\MP3\OK")
# Every review clip is capped below 45 seconds.  400 generated tokens leaves
# ample room for conversational Mandarin while avoiding the Python 3.14 /
# faster-whisper path that incorrectly adds an integer to None when the
# library default for max_new_tokens is used.
MAX_NEW_TOKENS = 400


class SilentProgress:
    """No-op replacement for faster-whisper's hidden progress bar.

    tqdm creates its monitor thread in ``__new__`` before its ``disable`` flag
    is processed.  Python 3.14 cannot run that monitor reliably in this local
    dependency stack, so merely passing ``log_progress=False`` is insufficient.
    The review never exposes progress output; faster-whisper only calls update
    and close on this object.
    """

    def __init__(self, *args, **kwargs) -> None:
        pass

    def update(self, *args, **kwargs) -> None:
        pass

    def close(self) -> None:
        pass


def disable_incompatible_console_progress() -> None:
    """Avoid Python-3.14 failures from hidden tqdm/colorama progress output.

    The review runs hidden and explicitly requests no progress output, so the
    monitor thread and colorama atexit hook add no value.  Under Python 3.14
    both can emit errors that make the batch file treat a completed review pass
    as failed.
    """
    tqdm.monitor_interval = 0
    faster_whisper_transcribe.tqdm = SilentProgress
    try:
        from colorama import deinit
        from colorama.initialise import reset_all
    except ImportError:
        return
    atexit.unregister(reset_all)
    deinit()


disable_incompatible_console_progress()


def audio_path(video_id: str) -> Path | None:
    candidate = AUDIO_ROOT / f"Oka_{video_id}.webm"
    if candidate.exists():
        return candidate
    return next(iter((ROOT / "data" / "audio_cache").glob(f"{video_id}.*")), None)


def atomic_write_reviews(reviews: dict, path: Path = REVIEWS) -> None:
    """Prevent quality reports from reading a half-written review ledger."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(reviews, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(temporary_name).replace(path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def load_audit() -> list[dict]:
    with gzip.open(AUDIT, "rt", encoding="utf-8") as handle:
        return json.load(handle)["paragraphs"]


def transcribe_clip(model: WhisperModel, audio: str, clip: str):
    """Transcribe one bounded review clip with Python-3.14-safe options."""
    return model.transcribe(
        audio,
        language="zh",
        vad_filter=True,
        clip_timestamps=clip,
        beam_size=5,
        log_progress=False,
        # A review clip is evidence for one paragraph.  Decoding VAD
        # subsegments independently prevents prior token accumulation from
        # overflowing Whisper's fixed 448-token context window under the
        # Python 3.14 stack.
        condition_on_previous_text=False,
        # An explicit empty string avoids the broken None initial-prompt path.
        initial_prompt="",
        # Explicitly avoid the broken None max_new_tokens path seen in the
        # local faster-whisper build under Python 3.14.
        max_new_tokens=MAX_NEW_TOKENS,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--ids",
        help="Comma-separated paragraph IDs. Use this for a targeted review instead of the audit queue.",
    )
    parser.add_argument("--models", default="small,medium,large-v3")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    model_names = [name.strip() for name in args.models.split(",") if name.strip()]
    if not model_names:
        parser.error("--models must contain at least one model name")

    existing = json.loads(REVIEWS.read_text(encoding="utf-8")) if REVIEWS.exists() else {}
    audit = load_audit()
    requested_ids = {value.strip() for value in (args.ids or "").split(",") if value.strip()}
    def needs_requested_models(paragraph: dict) -> bool:
        prior = existing.get(paragraph["id"], {})
        # Audio files can arrive after an earlier review run.  Re-check the
        # source instead of permanently excluding a paragraph based on stale
        # "unavailable" metadata.
        if prior.get("audio_status") == "unavailable" and not audio_path(paragraph["video_id"]):
            return False
        prior_asr = prior.get("asr", {})
        return any(name not in prior_asr for name in model_names)

    if requested_ids:
        found_ids = {paragraph["id"] for paragraph in audit}
        unknown_ids = sorted(requested_ids - found_ids)
        if unknown_ids:
            parser.error(f"Unknown paragraph IDs: {', '.join(unknown_ids)}")
        pending = [p for p in audit if p["id"] in requested_ids and needs_requested_models(p)]
    else:
        pending = [p for p in audit if p["needs_audio_review"] and needs_requested_models(p)]
    pending = pending[:args.limit]
    unavailable = [p for p in pending if not audio_path(p["video_id"])]
    missing = [p["id"] for p in unavailable]
    for paragraph in unavailable:
        existing[paragraph["id"]] = {
            "schema_version": 1,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "video_id": paragraph["video_id"],
            "start": paragraph["start"],
            "end": paragraph["end"],
            "raw_text": paragraph["raw_text"],
            "candidate_text": paragraph["candidate_text"],
            "flags": paragraph["flags"],
            "audio_status": "unavailable",
            "asr": {},
        }
    if unavailable and not args.dry_run:
        atomic_write_reviews(existing)
    pending = [p for p in pending if p not in unavailable]
    print(f"Pending: {len(pending)}; audio missing: {len(missing)}")
    if args.dry_run:
        for paragraph in pending[:10]:
            print(paragraph["id"], audio_path(paragraph["video_id"]))
        return

    for paragraph in pending:
        source = audio_path(paragraph["video_id"])
        if not source:
            print(f"Skipped {paragraph['id']}: source audio not found", file=sys.stderr)
            continue
        clip_start = max(0, paragraph["start"] - 2)
        clip_end = paragraph["end"] + 2
        prior = existing.get(paragraph["id"], {})
        existing[paragraph["id"]] = {
            "schema_version": 1,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "video_id": paragraph["video_id"],
            "title": paragraph["title"],
            "start": paragraph["start"],
            "end": paragraph["end"],
            "audio_path": str(source),
            "clip_start": clip_start,
            "clip_end": clip_end,
            "raw_text": paragraph["raw_text"],
            "candidate_text": paragraph["candidate_text"],
            "flags": paragraph["flags"],
            "asr": prior.get("asr", {}),
        }

    # Load one model at a time so a low-memory GPU can review the same clips.
    # Save after every clip; interrupted runs resume from the missing model output.
    for name in model_names:
        if not any(
            paragraph["id"] in existing and name not in existing[paragraph["id"]]["asr"]
            for paragraph in pending
        ):
            continue
        model = WhisperModel(name, device="cuda", compute_type="float16")
        for paragraph in pending:
            review = existing.get(paragraph["id"])
            if not review or name in review["asr"]:
                continue
            clip = f"{review['clip_start']:.2f},{review['clip_end']:.2f}"
            segments, _ = transcribe_clip(model, review["audio_path"], clip)
            review["asr"][name] = "".join(segment.text.strip() for segment in segments)
            review["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            atomic_write_reviews(existing)
            print(f"Reviewed {paragraph['id']} with {name}")
        del model
        gc.collect()


if __name__ == "__main__":
    main()
