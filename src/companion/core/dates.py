"""Weekday and month names, and a date written out in words. One home for what the features that
read a day from a sentence (calendar, open loops, reminders) share."""

from __future__ import annotations

import calendar
import re

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

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


def month_day(text: str) -> tuple[int, int] | None:
    """The first date written out in `text` ("December 4th", "4 dec", "the 4th of sept") as a month
    and a day (1 to 12, 1 to 99: the day is not checked against the month), or None."""
    found = _DATE.search(text)
    if found is None:
        return None
    return _MONTHS[(found["m"] or found["m2"]).lower()], int(found["d"] or found["d2"])
