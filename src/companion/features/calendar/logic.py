"""The days worth a word, chosen by code (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`).

Public and cultural days come from the `holidays` library for one region; a few cultural days are
also written here, used only when the library lacks them. The relationship's dates come from the day
of their first message. Their own dates (a birthday, an anniversary) are read by code from what
memory holds about them (`yearly`). A big day and each of theirs also has a lead-up two days and
one day before. Code picks at most one occasion a turn, in a fixed order, and never one already
offered. Pure.
"""

from __future__ import annotations

import calendar
import functools
import re
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
THEIRS_NOTE = get("notes/occasion-theirs")
OFFERED = "calendar: offered"
LOOKBACK = timedelta(days=3)  # how far back an offer counts: a lead-up is at most two days ahead


class Kind(StrEnum):
    PUBLIC = "public"
    CULTURAL = "cultural"
    RELATIONSHIP = "relationship"
    THEIRS = "theirs"  # a date of theirs from memory: a birthday, an anniversary


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


@dataclass(frozen=True, slots=True)
class Dated:
    """A date of theirs that comes round every year, read from a memory."""

    name: str  # "their birthday", "their sister's birthday"
    month: int
    day: int

    def on(self, year: int) -> date:
        """This year's day; the 29th of February is the 28th in other years."""
        return date(year, self.month, min(self.day, calendar.monthrange(year, self.month)[1]))


_MONTHS = {
    **{name.lower(): i for i, name in enumerate(calendar.month_name) if name},
    **{name.lower(): i for i, name in enumerate(calendar.month_abbr) if name},
    "sept": 9,
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE = re.compile(
    rf"\b(?:(?P<m>{_MONTH})\.?\s+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?"
    rf"|(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m2>{_MONTH}))\b",
    re.IGNORECASE,
)
_YEARLY = re.compile(r"\b(?:birthday|anniversary)\b|\bturns \d+\b", re.IGNORECASE)
_WHOSE = re.compile(
    r"\b(?:the user's|their)\s+((?:[a-z][\w-]*\s+){0,2}?[\w-]+)'s\s+(birthday|anniversary)",
    re.IGNORECASE,
)
# A date tied to a loss is never marked, whatever memory's sensitivity says.
_HARD = re.compile(
    r"\b(?:die[ds]?|dying|death|dead|passed(?: away)?|killed|suicide|funeral|grave|loss|lost"
    r"|miscarriage|divorced?|broke up|breakup|accident|diagnos\w*)\b",
    re.IGNORECASE,
)


def yearly(claim: str) -> Dated | None:
    """The yearly date a memory names (a birthday or an anniversary on a month and a day), or None.
    Their own when no one else's is named; never one tied to a loss."""
    found = _DATE.search(claim)
    if found is None or _YEARLY.search(claim) is None or _HARD.search(claim) is not None:
        return None
    month = _MONTHS[(found["m"] or found["m2"]).lower()]
    day = int(found["d"] or found["d2"])
    if not 1 <= day <= calendar.monthrange(2024, month)[1]:
        return None
    other = _WHOSE.search(claim)
    if other is not None:
        return Dated(f"their {other[1]}'s {other[2].lower()}", month, day)
    what = "anniversary" if "anniversary" in claim.lower() else "birthday"
    return Dated(f"their {what}", month, day)


SENSITIVE = 2  # a memory this sensitive never gives a date: such a day is never marked on its own


def their_dates(memories: Sequence[tuple[str, int]]) -> tuple[Dated, ...]:
    """Their yearly dates from what memory holds, as (claim, sensitivity), each once."""
    found = (yearly(claim) for claim, level in memories if level < SENSITIVE)
    return tuple(dict.fromkeys(d for d in found if d is not None))


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


def occasions(
    today: date, region: str, first_met: date | None, theirs: Collection[Dated] = ()
) -> list[Occasion]:
    """What today holds: their own dates, the relationship's date, the public and cultural days,
    and the lead-ups to one of theirs or a big day one or two days ahead."""
    out = [
        Occasion(d.name, today, Kind.THEIRS, How.ON_THE_DAY)
        for d in theirs
        if d.on(today.year) == today
    ]
    span = together(today, first_met) if first_met is not None else None
    if span is not None:
        out.append(Occasion(span, today, Kind.RELATIONSHIP, How.ON_THE_DAY))
    out.extend(Occasion(name, today, kind, How.ON_THE_DAY) for name, kind in _on(today, region))
    for ahead in sorted(LEAD, reverse=True):
        day = today + timedelta(days=ahead)
        out.extend(
            Occasion(d.name, day, Kind.THEIRS, How.LEAD_UP) for d in theirs if d.on(day.year) == day
        )
        out.extend(
            Occasion(name, day, kind, How.LEAD_UP) for name, kind in _on(day, region) if name in BIG
        )
    return out


def _rank(o: Occasion) -> int:
    """Theirs first, then the relationship's, then a public or cultural day; lead-ups after the
    days themselves, theirs first."""
    if o.how is How.LEAD_UP:
        return 3 if o.kind is Kind.THEIRS else 4
    return {Kind.THEIRS: 0, Kind.RELATIONSHIP: 1}.get(o.kind, 2)


def pick(found: Sequence[Occasion], offered: Collection[str]) -> Occasion | None:
    """The one occasion for this turn: one of theirs, the relationship's day, a public or cultural
    day, then a lead-up (theirs first); never one whose key was already offered."""
    fresh = [o for o in found if o.key not in offered]
    return min(fresh, key=_rank) if fresh else None


def when(o: Occasion, today: date) -> str:
    """How far off it is, in words: "today", "tomorrow" or "in two days"."""
    return LEAD.get((o.day - today).days, "today")


def note(o: Occasion, today: date) -> str:
    """The line sent after the history."""
    if o.kind is Kind.RELATIONSHIP:
        return US_NOTE.render(span=o.name)
    if o.kind is Kind.THEIRS and o.how is How.ON_THE_DAY:
        return THEIRS_NOTE.render(name=o.name)
    if o.how is How.LEAD_UP:
        return SOON_NOTE.render(name=o.name[:1].upper() + o.name[1:], when=when(o, today))
    return DAY_NOTE.render(name=o.name)
