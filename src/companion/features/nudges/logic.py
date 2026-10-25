"""A light nudge after they stepped away and stayed gone longer than they said (shadow).

"gonna shower" and then two hours of quiet is the moment a friend sends "damn, long shower 👀". The
owner asked for the looser rule (also when they did not say they would be back) to see how it does.
A time away is a `leaving` label from the reader of what is happening with them now (ADR 0024,
`core/turn/now.py`); code decides: one nudge per
time away, only after twice the time and at least an hour, never in quiet hours, never after a
goodbye, gone after six hours, at most two a day, and any message from them cancels it. Drafts are
logged and nothing is sent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from companion.core.reachout import Held
from companion.core.turn.now import Phase, Said
from companion.core.types import Json
from companion.prompts import get

DRAFT = get("system/nudge-draft")
MIN_WAIT = timedelta(hours=1)
GONE = timedelta(hours=6)
PER_DAY = 2


DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


@dataclass(frozen=True, slots=True)
class Away:
    turn: str
    said: str
    minutes: int
    at: datetime


def wait(a: Away) -> timedelta:
    return max(MIN_WAIT, timedelta(minutes=2 * a.minutes))


@dataclass(frozen=True, slots=True)
class Look:
    """What the tick reads: the newest time away, their newest message, and the nudges so far."""

    away: Away | None
    last_theirs: datetime | None
    nudged: frozenset[str]  # turns already nudged, or tried and dropped
    nudges_today: int


def due(look: Look, now: datetime, held: Held | None) -> tuple[Away | None, str]:
    """The time away to nudge about now, or None with the first reason that holds it. `held` is the
    shared gate's answer for any reach-out now (ADR 0023): quiet hours, a scene, an active chat,
    the last one unanswered, the gap, the share and a crisis turn."""
    a = look.away
    if a is None:
        return None, "no time away"
    holds = (
        (look.last_theirs is not None and look.last_theirs > a.at, "they came back"),
        (a.turn in look.nudged, "already nudged about it"),
        (now - a.at > GONE, "gone too long; past nudging"),
        (now - a.at < wait(a), "not long enough yet"),
        (look.nudges_today >= PER_DAY, f"already {look.nudges_today} today"),
        (held is not None, held.why if held is not None else ""),
    )
    why = next((why for hit, why in holds if hit), None)
    if why is not None:
        return None, why
    gone = (now - a.at).total_seconds() / 60
    return a, f"stepped away {gone:.0f} minutes ago, about {a.minutes} expected"


def draft_prompt(a: Away, now: datetime) -> str:
    return f"They said: {a.said!r}\nThat was {(now - a.at).total_seconds() / 60:.0f} minutes ago."


def newest(aways: Sequence[Away]) -> Away | None:
    return max(aways, key=lambda a: a.at, default=None)


def aways(said: Sequence[Said]) -> list[Away]:
    """The times they said they were leaving now, from the labels of what is happening with them."""
    return [
        Away(s.turn, s.text, s.label.minutes, s.at) for s in said if s.label.phase is Phase.LEAVING
    ]
