"""Conservative paragraphing and QA for the transcript corpus.

Raw ASR text is retained unchanged.  This module produces paragraph candidates
with auditable correction suggestions; an audio comparison must approve any
correction before it becomes public text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from transcript_corrections import apply_corrections

MIN_CHARS = 80
TARGET_CHARS = 150
MAX_CHARS = 210
MAX_SECONDS = 45
PAUSE_SECONDS = 3.8
STRONG_TOPIC_CUES = ("首先", "第一", "第二", "第三", "接下來", "另外", "最後", "總結")


@dataclass
class Paragraph:
    start: float
    end: float
    raw_text: str
    corrected_text: str
    flags: list[str]


def compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def proposed_corrections(text: str) -> tuple[str, list[str]]:
    """Apply only context-safe candidate corrections; do not claim they are final."""
    corrected, flags = apply_corrections(text)
    if re.search(r"(.)\1\1", corrected):
        flags.append("repeated characters")
    if len(corrected) < 24:
        flags.append("too short for a reliable guide")
    return corrected, flags


def paragraphize(chunks: list[dict]) -> list[Paragraph]:
    """Group neighbouring ASR cuts using pause, discourse, and length bounds."""
    ordered = sorted(chunks, key=lambda item: float(item.get("start", 0) or 0))
    groups: list[list[dict]] = []
    current: list[dict] = []

    for chunk in ordered:
        if not compact(chunk.get("text", "")):
            continue
        if not current:
            current.append(chunk)
            continue

        current_text = compact("".join(str(item.get("text", "")) for item in current))
        previous = current[-1]
        next_text = compact(chunk.get("text", ""))
        gap = float(chunk.get("start", 0) or 0) - float(previous.get("start", 0) or 0)
        duration = float(chunk.get("start", 0) or 0) - float(current[0].get("start", 0) or 0)
        previous_ends_sentence = bool(re.search(r"[。！？!?]$", str(previous.get("text", "")).strip()))
        next_is_new_topic = next_text.startswith(STRONG_TOPIC_CUES)
        enough_context = len(current_text) >= MIN_CHARS

        should_close = (
            len(current_text) >= MAX_CHARS
            or duration >= MAX_SECONDS
            or (enough_context and gap >= PAUSE_SECONDS)
            or (len(current_text) >= TARGET_CHARS and previous_ends_sentence)
            or (len(current_text) >= TARGET_CHARS and next_is_new_topic)
        )
        if should_close:
            groups.append(current)
            current = [chunk]
        else:
            current.append(chunk)

    if current:
        groups.append(current)

    paragraphs = []
    for group in groups:
        raw_text = compact("".join(str(item.get("text", "")) for item in group))
        corrected_text, flags = proposed_corrections(raw_text)
        paragraphs.append(Paragraph(
            start=float(group[0].get("start", 0) or 0),
            end=float(group[-1].get("start", 0) or 0),
            raw_text=raw_text,
            corrected_text=corrected_text,
            flags=flags,
        ))
    return paragraphs
