"""What every reach-out keeps to, whatever prompted it (a plan of theirs, a time away): the caps,
the quiet hours, and how short a drafted message must be. Pure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, tzinfo

MAX_DRAFT_WORDS = 18


@dataclass(frozen=True, slots=True)
class Caps:
    quiet_start: time = time(23, 0)
    quiet_end: time = time(8, 0)
    max_per_day: int = 1
    min_gap_hours: float = 20.0
    user_quiet_minutes: int = 90
    expire_days: float = 2.0
    backoff_hours: float = 72.0  # after one reach-out went unanswered
    max_unanswered: int = 2  # after this many in a row, wait for them to write first


def in_quiet_hours(now: datetime, tz: tzinfo, caps: Caps) -> bool:
    t = now.astimezone(tz).time()
    if caps.quiet_start <= caps.quiet_end:
        return caps.quiet_start <= t < caps.quiet_end
    return t >= caps.quiet_start or t < caps.quiet_end


def short_draft(message: str) -> str:
    """The draft if it is short, its first sentence if that is a short question, else none."""
    text = " ".join(message.split())
    if len(text.split()) <= MAX_DRAFT_WORDS:
        return text
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    short = len(first.split()) <= MAX_DRAFT_WORDS and first.endswith("?")
    return first if short else ""
