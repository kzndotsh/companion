"""The days worth a word, chosen by code (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`).

Public and cultural days come from the `holidays` library for one region; a few cultural days are
also written here, used only when the library lacks them. The relationship's dates come from the day
of their first message. A big day also has a lead-up two days and one day before. Code picks at
most one occasion a turn, in a fixed order, and never one already offered. Pure.
"""

from __future__ import annotations

import calendar
import functools
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

import holidays

from companion.prompts import get

REGION = "US"  # the one place the region is set, until where they live is known
DAY_NOTE = get("notes/occasion-day")
SOON_NOTE = get("notes/occasion-soon")
US_NOTE = get("notes/occasion-us")
OFFERED = "calendar: offered"
LOOKBACK = timedelta(days=3)  # how far back an offer counts: a lead-up is at most two days ahead


class Kind(StrEnum):
    PUBLIC = "public"
    CULTURAL = "cultural"
    RELATIONSHIP = "relationship"


class How(StrEnum):
    ON_THE_DAY = "on_the_day"
    LEAD_UP = "lead_up"


@dataclass(frozen=True, slots=True)
class Occasion:
    name: str  # plain wording; for the relationship, the span ("a month", "a year")
    day: date  # the day itself; for a lead-up, the big day it leads up to
    kind: Kind
    how: How

    @property
    def key(self) -> str:
        """What an offer is logged and matched by. A lead-up's key has no distance in it, so the
        two-days and the one-day lead-up are one offer: once per big day."""
        return f"{self.how}:{self.name}:{self.day.isoformat()}"


# The library's names in plain words; a name not here is used as it is.
PLAIN = {
    "Washington's Birthday": "Presidents' Day",
    "Juneteenth National Independence Day": "Juneteenth",
    "Thanksgiving Day": "Thanksgiving",
    "Saint Patrick's Day": "St. Patrick's Day",
    "Easter Sunday": "Easter",
}
# Days of remembrance, civic or religious days, and contested ones are left out: replayed with the
# day's note, it wished people a "happy Memorial Day" and a "happy Good Friday" (2026-10-25).
LEFT_OUT = frozenset(
    {
        "Martin Luther King Jr. Day",
        "Presidents' Day",
        "Memorial Day",
        "Juneteenth",
        "Columbus Day",
        "Veterans Day",
        "Good Friday",
    }
)
BIG = frozenset({"New Year's Eve", "Valentine's Day", "Halloween", "Thanksgiving", "Christmas Day"})
LEAD = {1: "tomorrow", 2: "in two days"}


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def fallback_days(year: int) -> dict[str, date]:
    """Cultural days written here, added only when the library lacks them for the region."""
    return {
        "New Year's Eve": date(year, 12, 31),
        "Christmas Eve": date(year, 12, 24),
        "Mother's Day": _nth_sunday(year, 5, 2),
        "Father's Day": _nth_sunday(year, 6, 3),
    }


@functools.cache
def _days(year: int, region: str) -> tuple[tuple[date, str, Kind], ...]:
    """Every public and cultural day of a year, in plain words, observed stand-ins left out."""
    out: list[tuple[date, str, Kind]] = []
    for category, kind in ((holidays.PUBLIC, Kind.PUBLIC), (holidays.UNOFFICIAL, Kind.CULTURAL)):
        found = holidays.country_holidays(region, years=year, categories=category, observed=False)
        for day, names in sorted(found.items()):
            plain = (PLAIN.get(n, n) for n in str(names).split("; "))
            out.extend((day, name, kind) for name in plain if name not in LEFT_OUT)
    named = {name for _, name, _ in out}
    out.extend(
        (day, name, Kind.CULTURAL) for name, day in fallback_days(year).items() if name not in named
    )
    return tuple(sorted(out, key=lambda d: d[0]))


def _on(day: date, region: str) -> list[tuple[str, Kind]]:
    return [(name, kind) for d, name, kind in _days(day.year, region) if d == day]


def add_months(start: date, months: int) -> date:
    """The same day `months` later; past a short month's end, its last day."""
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


_YEARS = ("a year", "two years", "three years", "four years", "five years")


def _span(years: int) -> str:
    return _YEARS[years - 1] if years <= len(_YEARS) else f"{years} years"


def together(today: date, first_met: date) -> str | None:
    """The span when today is one of the relationship's dates, or None."""
    if today == add_months(first_met, 1):
        return "a month"
    if today == first_met + timedelta(days=100):
        return "a hundred days"
    if today == add_months(first_met, 6):
        return "six months"
    years = today.year - first_met.year
    if years >= 1 and today == add_months(first_met, 12 * years):
        return _span(years)
    return None


def occasions(today: date, region: str, first_met: date | None) -> list[Occasion]:
    """What today holds: the relationship's date, the public and cultural days, and the lead-ups
    to a big day one or two days ahead."""
    out: list[Occasion] = []
    span = together(today, first_met) if first_met is not None else None
    if span is not None:
        out.append(Occasion(span, today, Kind.RELATIONSHIP, How.ON_THE_DAY))
    out.extend(Occasion(name, today, kind, How.ON_THE_DAY) for name, kind in _on(today, region))
    for ahead in sorted(LEAD, reverse=True):
        day = today + timedelta(days=ahead)
        out.extend(
            Occasion(name, day, kind, How.LEAD_UP) for name, kind in _on(day, region) if name in BIG
        )
    return out


def _rank(o: Occasion) -> int:
    if o.how is How.LEAD_UP:
        return 2
    return 0 if o.kind is Kind.RELATIONSHIP else 1


def pick(found: Sequence[Occasion], offered: Collection[str]) -> Occasion | None:
    """The one occasion for this turn: the relationship's day, then a public or cultural day, then a
    lead-up; never one whose key was already offered."""
    fresh = [o for o in found if o.key not in offered]
    return min(fresh, key=_rank) if fresh else None


def when(o: Occasion, today: date) -> str:
    """How far off it is, in words: "today", "tomorrow" or "in two days"."""
    return LEAD.get((o.day - today).days, "today")


def note(o: Occasion, today: date) -> str:
    """The line sent after the history."""
    if o.kind is Kind.RELATIONSHIP:
        return US_NOTE.render(span=o.name)
    if o.how is How.LEAD_UP:
        return SOON_NOTE.render(name=o.name, when=when(o, today))
    return DAY_NOTE.render(name=o.name)
