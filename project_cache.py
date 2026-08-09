"""Keep model and package caches inside this project, not the system drive."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CACHE_ROOT = ROOT / ".cache"


def configure_project_cache() -> Path:
    """Configure cache locations before importing model libraries."""
    huggingface = CACHE_ROOT / "huggingface"
    modelscope = CACHE_ROOT / "modelscope"
    torch = CACHE_ROOT / "torch"
    pip = CACHE_ROOT / "pip"
    for directory in (huggingface, modelscope, torch, pip):
        directory.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(huggingface)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(huggingface / "hub")
    os.environ["MODELSCOPE_CACHE"] = str(modelscope)
    os.environ["TORCH_HOME"] = str(torch)
    os.environ["PIP_CACHE_DIR"] = str(pip)
    return CACHE_ROOT
