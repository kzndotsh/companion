"""The parts of the local day, defined once: where morning, afternoon, evening and night begin.

A feature that needs a part of the day reads it here. A feature whose rule is about something else
that happens to fall on the clock (when their day rolls over, what time a reminder goes out)
keeps its own named boundary and says what it is for.
"""

from __future__ import annotations

from enum import StrEnum


class DayPart(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


MORNING_FROM = 5  # the local hour each part begins; night runs from NIGHT_FROM past midnight
AFTERNOON_FROM = 12
EVENING_FROM = 17
NIGHT_FROM = 22


def part_of_day(hour: int) -> DayPart:
    """The part a local hour (0 to 23) falls in."""
    if hour >= NIGHT_FROM or hour < MORNING_FROM:
        return DayPart.NIGHT
    if hour < AFTERNOON_FROM:
        return DayPart.MORNING
    return DayPart.AFTERNOON if hour < EVENING_FROM else DayPart.EVENING
