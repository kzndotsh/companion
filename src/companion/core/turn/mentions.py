"""What the companion brings up on its own, chosen once a turn across every source (ADR 0023): the
rank that orders them, a candidate's shape, the choice, and the pace learned from how they met the
last ones (shadow). Pure.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum

from companion.core.types import Json
from companion.prompts import get


class Rank(IntEnum):
    """Which comes first when several fit, lower first. A day that passes beats what can wait."""

    THEIRS = 0  # their own day: a birthday or anniversary from memory, a celebration of theirs
    FACING = 1  # something big they face today, a word of cheering
    US = 2  # the relationship's own date
    DAY = 3  # a public or cultural day
    FOLLOW_UP = 4  # how something of theirs went
    LEAD_UP = 5  # a day of theirs or a big day coming in a day or two


@dataclass(frozen=True, slots=True)
class MentionCandidate:
    """One thing a source would bring up this turn. Its line is the note sent as is, in the system
    block or after the history; `key` and `detail` are the decision logged once the turn is
    stored, and `write` any write of the source's own then (a plan marked asked)."""

    rank: Rank
    line: str
    tail: bool
    key: str
    about: str  # the thing in plain words, logged and read back by how they met it
    detail: dict[str, Json] = field(default_factory=dict[str, Json])
    reason: str | None = None
    write: Callable[[], None] | None = None


WINDOW = timedelta(hours=24)
# The check-in after a heavy talk is its own note (it comes at serious moments the others wait
# out), but it counts toward the pace and how it was met is read like the others.
CHECKED_IN = "check-in: asked how they are after a heavy last talk"


def choose(found: Sequence[MentionCandidate], recent: Sequence[Rank]) -> MentionCandidate | None:
    """The one to bring up: the best rank not held back by something of the same or a better rank
    brought up in the last day, so one a day across sources, but a birthday never waits behind a
    morning's follow-up. Equal ranks keep their sources' order."""
    best = min(recent, default=None)
    allowed = [c for c in found if best is None or c.rank < best]
    return min(allowed, key=lambda c: c.rank, default=None)


class Met(StrEnum):
    """How they met a thread it brought up, read from their next message (ADR 0023)."""

    PICKED_UP = "picked_up"
    BRUSHED_OFF = "brushed_off"
    IGNORED = "ignored"


MET_PROMPT = get("system/thread-met")
MET_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"met": {"type": "string", "enum": [m.value for m in Met]}},
    "required": ["met"],
    "additionalProperties": False,
}


def parse_met(data: Json) -> Met | None:
    met = data.get("met") if isinstance(data, dict) else None
    return next((m for m in Met if m.value == met), None)


def met_prompt(claim: str, brought_up: str, theirs: str) -> str:
    return f"BROUGHT UP: {claim}\nCOMPANION: {brought_up}\nUSER: {theirs}"


# The wait before it brings up the next thread, learned from how they met the last ones (ADR 0023).
# It starts at a day, as each kind allowed before; picked up is a step shorter, brushed off a step
# longer, ignored two. Walked oldest first, so the newest answers decide where it stands.
PACE = tuple(timedelta(hours=h) for h in (4, 8, 16, 24, 48, 96))
PACE_START = 3
PACE_STEP = {Met.PICKED_UP: -1, Met.BRUSHED_OFF: 1, Met.IGNORED: 2}
PACE_CEILING = 3  # in any 24 hours: a backstop while it knows little, never a target
PACE_LOOKBACK = timedelta(days=30)


def pace(mets: Sequence[Met]) -> timedelta:
    at = PACE_START
    for m in mets:
        at = min(max(at + PACE_STEP[m], 0), len(PACE) - 1)
    return PACE[at]


def pace_holds(wait: timedelta, offered: Sequence[datetime], now: datetime) -> str | None:
    """Why the learned pace would wait now, or None when it would bring one up."""
    last = max(offered, default=None)
    if last is not None and now - last < wait:
        return f"the last was {(now - last).total_seconds() / 3600:.1f}h ago, under its {_h(wait)}"
    today = sum(1 for at in offered if now - at < timedelta(days=1))
    if today >= PACE_CEILING:
        return f"{today} in the last 24 hours, at the ceiling of {PACE_CEILING}"
    return None


def _h(wait: timedelta) -> str:
    return f"{wait.total_seconds() / 3600:.0f}h pace"
