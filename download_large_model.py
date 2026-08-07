"""Download the local-only Whisper large-v3 model with resumable Hugging Face cache."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".python-packages"))

from faster_whisper import WhisperModel

parser = argparse.ArgumentParser()
parser.add_argument("model", nargs="?", default="large-v3")
args = parser.parse_args()
print(f"Starting {args.model} download/load", flush=True)
WhisperModel(args.model, device="cpu", compute_type="int8")
print(f"{args.model} ready", flush=True)
