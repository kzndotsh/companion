"""A light nudge after they stepped away and stayed gone longer than they said (shadow).

"gonna shower" and then two hours of quiet is the moment a friend sends "damn, long shower 👀". The
owner asked for the looser rule (also when they did not say they would be back) to see how it does.
A small model reads whether a message steps away and for about how long; code decides: one nudge per
time away, only after twice the time and at least an hour, never in quiet hours, never after a
goodbye, gone after six hours, at most two a day, and any message from them cancels it. Drafts are
logged and nothing is sent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from enum import StrEnum

from companion.core.reachout import Caps, in_quiet_hours
from companion.core.types import Json
from companion.prompts import get

PROMPT = get("system/away")
DRAFT = get("system/nudge-draft")
AWAY = "away: they stepped away"
MIN_WAIT = timedelta(hours=1)
GONE = timedelta(hours=6)
PER_DAY = 2
MINUTES = (10, 180)  # a guess outside this is clamped


class Kind(StrEnum):
    BRIEF = "brief"
    BACK = "back"


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "away": {"type": "string", "enum": ["brief", "back", "goodbye", "none"]},
        "minutes": {"type": "integer"},
    },
    "required": ["away", "minutes"],
}
DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


@dataclass(frozen=True, slots=True)
class Away:
    turn: str
    said: str
    kind: Kind
    minutes: int
    at: datetime


def parse(data: Json) -> tuple[Kind, int] | None:
    """The kind of stepping away and the minutes, clamped. None for a goodbye, none or bad data."""
    if not isinstance(data, dict):
        return None
    kind, minutes = data.get("away"), data.get("minutes")
    if kind not in set(Kind) or not isinstance(minutes, int) or isinstance(minutes, bool):
        return None
    return Kind(str(kind)), max(MINUTES[0], min(MINUTES[1], minutes))


@dataclass(frozen=True, slots=True)
class Answer:
    """A readable answer: the time away, or None for a goodbye or not stepping away at all."""

    away: tuple[Kind, int] | None


def read(data: Json) -> Answer | None:
    """The judge's answer; None only when it cannot be read, so "not stepping away" is not a
    failure in the log."""
    if isinstance(data, dict) and data.get("away") in ("goodbye", "none"):
        return Answer(None)
    found = parse(data)
    return None if found is None else Answer(found)


def wait(a: Away) -> timedelta:
    return max(MIN_WAIT, timedelta(minutes=2 * a.minutes))


@dataclass(frozen=True, slots=True)
class Look:
    """What the tick reads: the newest time away, their newest message, and the nudges so far."""

    away: Away | None
    last_theirs: datetime | None
    nudged: frozenset[str]  # turns already nudged
    nudges_today: int


def due(look: Look, now: datetime, tz: tzinfo, caps: Caps = Caps()) -> tuple[Away | None, str]:  # noqa: B008
    """The time away to nudge about now, or None with the first reason that holds it."""
    a = look.away
    if a is None:
        return None, "no time away"
    holds = (
        (look.last_theirs is not None and look.last_theirs > a.at, "they came back"),
        (a.turn in look.nudged, "already nudged about it"),
        (now - a.at > GONE, "gone too long; past nudging"),
        (now - a.at < wait(a), "not long enough yet"),
        (in_quiet_hours(now, tz, caps), "quiet hours"),
        (look.nudges_today >= PER_DAY, f"already {look.nudges_today} today"),
    )
    held = next((why for hit, why in holds if hit), None)
    if held is not None:
        return None, held
    gone = (now - a.at).total_seconds() / 60
    return a, f"stepped away {gone:.0f} minutes ago, about {a.minutes} expected"


def draft_prompt(a: Away, now: datetime) -> str:
    return f"They said: {a.said!r}\nThat was {(now - a.at).total_seconds() / 60:.0f} minutes ago."


def newest(aways: Sequence[Away]) -> Away | None:
    return max(aways, key=lambda a: a.at, default=None)
