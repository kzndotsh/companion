"""How long a belief stays worth asserting. Beliefs are never deleted; they stop being asserted.

Age is measured from the freshest evidence, so a belief the user restates stays fresh. The horizons
below are guesses taken from the constants other projects use (a week for episodic things, months
for facts). They are written down so they can be tuned with use, not because they are right.
"""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from enum import StrEnum

from companion.core.types import BeliefKind


class Freshness(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"


# Days a belief of this kind is worth asserting. None means it is history and never goes stale.
HORIZON_DAYS: dict[BeliefKind, int | None] = {
    BeliefKind.TRAIT: 365,
    BeliefKind.PREFERENCE: 365,
    BeliefKind.BOUNDARY: 365,
    BeliefKind.TELL: 365,
    BeliefKind.THREAD: 30,
    BeliefKind.PROMISE: 30,
    BeliefKind.STATE: 14,
    BeliefKind.EVENT: None,
}


def status(kind: BeliefKind, last_supported: datetime, now: datetime) -> Freshness:
    horizon = HORIZON_DAYS[kind]
    if horizon is None:
        return Freshness.FRESH
    age = now - last_supported
    if age <= timedelta(days=horizon / 2):
        return Freshness.FRESH
    return Freshness.AGING if age <= timedelta(days=horizon) else Freshness.STALE


def when_phrase(last: datetime, now: datetime, tz: tzinfo | None = None) -> str:
    """How long ago, in the user's calendar days: something said at 5 pm yesterday is "yesterday"
    at 9 am today, however few hours have passed. `tz` defaults to the machine's local zone, the
    same one the clock line shows."""
    days = max((now.astimezone(tz).date() - last.astimezone(tz).date()).days, 0)
    if days < 1:
        return "today"
    if days < 2:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"
