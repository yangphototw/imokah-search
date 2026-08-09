"""Move this project's completed local model caches off the system drive.

Run only after `run_full_transcript_review.bat` is no longer running.  The
script moves exact, known model directories; it never clears a broad user cache
and refuses to overwrite an existing project copy.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from project_cache import CACHE_ROOT, configure_project_cache


MODEL_NAMES = (
    "models--Systran--faster-whisper-small",
    "models--Systran--faster-whisper-medium",
    "models--Systran--faster-whisper-large-v3",
)


def legacy_huggingface_hub() -> Path:
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    return user_profile / ".cache" / "huggingface" / "hub"


def migration_plan(source_root: Path, destination_root: Path) -> list[tuple[Path, Path]]:
    return [
        (source_root / model_name, destination_root / model_name)
        for model_name in MODEL_NAMES
        if (source_root / model_name).exists()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--move", action="store_true", help="Perform the safe move; omit for a dry-run plan.")
    args = parser.parse_args()

    configure_project_cache()
    source_root = legacy_huggingface_hub()
    destination_root = CACHE_ROOT / "huggingface" / "hub"
    plan = migration_plan(source_root, destination_root)
    if not plan:
        print("No known project Whisper caches remain under the legacy C-drive cache.")
        return

    for source, destination in plan:
        print(f"{source} -> {destination}")
    if not args.move:
        print("Dry run only. After the audio review process stops, rerun with --move.")
        return

    for source, destination in plan:
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite existing cache: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        print(f"Moved {source.name}")


if __name__ == "__main__":
    main()
