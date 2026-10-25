"""What reach-outs share: a hold from the shared gate (`Held`, ADR 0023), the caps and fixed quiet
hours nudges still keep, how long a plan keeps, and how a draft is tidied. Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, tzinfo

# The key of a nudge it would send (features/nudges), read by any reach-out that counts its own.
WOULD_NUDGE = "nudge (shadow): would send"


@dataclass(frozen=True, slots=True)
class Held:
    """The shared gate's hold on any reach-out (ADR 0023): which hold, the same from tick to tick,
    and the reason with its numbers."""

    what: str
    why: str


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


def draft_text(message: str) -> str:
    """The draft as the model wrote it, spacing tidied; empty when it wrote nothing. A long draft is
    neither cut nor dropped: the drafting prompts ask for a short message, and code never edits
    one (the owner's choice, 2026-10-25; before, a draft over 18 words was cut to its first
    sentence when that was a question, else dropped)."""
    return " ".join(message.split())
