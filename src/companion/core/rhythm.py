"""Their rhythm, learned from when they write (ADR 0021). Pure.

From the times of their own messages over the last two weeks: their pauses between conversations (a
conversation starts after two hours or more of quiet), the 75th percentile of those pauses, the
hours of the day they write, and the hours they almost never write. Before there is history it is a
baseline: a 12-hour pause and waking hours of 9 AM to 10 PM, with 11 PM to 8 AM quiet. The two are
blended by how many conversations it has seen, with full weight on theirs from 20, and the pause
that counts as missing them is never under 8 hours.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from itertools import pairwise

from companion.core.types import Json

WINDOW = timedelta(days=14)
NEW_CONVERSATION = timedelta(hours=2)
BASE_PAUSE_HOURS = 12.0
FLOOR_HOURS = 8.0
WAKING = range(9, 22)  # 9 AM to 10 PM
BASE_QUIET = frozenset({23, 0, 1, 2, 3, 4, 5, 6, 7})  # 11 PM to 8 AM
FULL_WEIGHT = 20  # conversations seen before their own numbers count fully
USUAL = 0.5  # an hour is usual when its blended score reaches this
QUIET = 0.9  # and quiet when its blended quiet score reaches this
RARE = 0.1  # an hour written in on under a tenth of the days of their busiest hour
KEPT_DAYS = 7
KEPT_MOST = 5  # a time they keep: the same hour on at least this many of the last 7 days


def starts(times: Sequence[datetime]) -> list[datetime]:
    """When each conversation began: the first time, and each after a pause of two hours or more."""
    ordered = sorted(times)
    return [t for i, t in enumerate(ordered) if i == 0 or t - ordered[i - 1] >= NEW_CONVERSATION]


def pauses(times: Sequence[datetime]) -> list[float]:
    """The pauses between their conversations, in hours."""
    ordered = sorted(times)
    gaps = (b - a for a, b in pairwise(ordered))
    return [g.total_seconds() / 3600 for g in gaps if g >= NEW_CONVERSATION]


def percentile(values: Sequence[float], q: float) -> float:
    """Linear between the closest ranks; values must not be empty."""
    ordered = sorted(values)
    at = (len(ordered) - 1) * q
    low = int(at)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (at - low)


def _hour_share(times: Sequence[datetime], tz: tzinfo) -> list[float]:
    """For each local hour, the days they wrote in it, as a share of their busiest hour's days."""
    days: list[set[object]] = [set() for _ in range(24)]
    for t in times:
        local = t.astimezone(tz)
        days[local.hour].add(local.date())
    top = max(len(d) for d in days)
    return [len(d) / top if top else 0.0 for d in days]


@dataclass(frozen=True, slots=True)
class Rhythm:
    conversations: int  # conversations of theirs seen in the window
    weight: float  # how much of the numbers is theirs, 0 (baseline) to 1
    learned_pause: float | None  # their 75th percentile pause in hours, None without one
    pause: float  # the blended pause past which it may miss them, in hours, never under 8
    usual: frozenset[int]  # local hours they usually write in
    quiet: frozenset[int]  # local hours they almost never write in

    def detail(self) -> dict[str, Json]:
        usual: list[Json] = [*sorted(self.usual)]
        quiet: list[Json] = [*sorted(self.quiet)]
        return {
            "conversations": self.conversations,
            "weight": round(self.weight, 2),
            "learned_pause_h": None if self.learned_pause is None else round(self.learned_pause, 1),
            "pause_h": round(self.pause, 1),
            "usual": usual,
            "quiet": quiet,
        }


def learn(theirs: Sequence[datetime], now: datetime, tz: tzinfo) -> Rhythm:
    """Their rhythm from their messages in the two weeks before `now`."""
    seen = [t for t in theirs if now - WINDOW <= t <= now]
    n = len(starts(seen))
    w = min(1.0, n / FULL_WEIGHT)
    gaps = pauses(seen)
    learned = percentile(gaps, 0.75) if gaps else None
    mine = BASE_PAUSE_HOURS if learned is None else learned
    pause = max(FLOOR_HOURS, (1 - w) * BASE_PAUSE_HOURS + w * mine)
    share = _hour_share(seen, tz) if seen else [0.0] * 24
    quiet = frozenset(
        h for h in range(24) if (1 - w) * (h in BASE_QUIET) + w * (share[h] < RARE) >= QUIET
    )
    usual = frozenset(
        h for h in range(24) if h not in quiet and (1 - w) * (h in WAKING) + w * share[h] >= USUAL
    )
    return Rhythm(n, w, learned, pause, usual, quiet)


def kept_hour(theirs: Sequence[datetime], now: datetime, tz: tzinfo) -> int | None:
    """The local hour they wrote in on most of the last seven days before today, or None."""
    today = now.astimezone(tz).date()
    first = today - timedelta(days=KEPT_DAYS)
    days: list[set[object]] = [set() for _ in range(24)]
    for t in theirs:
        local = t.astimezone(tz)
        if first <= local.date() < today:
            days[local.hour].add(local.date())
    best = max(range(24), key=lambda h: (len(days[h]), -h))
    return best if len(days[best]) >= KEPT_MOST else None
