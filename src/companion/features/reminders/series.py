"""Repeating reminders, check-ins and greetings: "remind me every day at 9 to take my meds", "tell
me good morning every day". A series is the standing request; each time it falls is an ordinary
reminder row with the series' id and its number in it, made once the one before has ended. Pure:
the rules for when it falls, when a greeting is skipped, when a series pauses, and the set note.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, tzinfo
from statistics import median

from companion.features.reminders.logic import (
    PARTS,
    WEEKDAYS,
    Kind,
    Part,
    Reminder,
    Repeat,
    Series,
    Slots,
    Standing,
    asked_for,
    clock_of,
    spoken,
)
from companion.prompts import get

REPEAT_NOTE = get("notes/reminder-repeat")
HOW_OFTEN = "how often: it can repeat every day, or on one day each week"
DAY_STARTS = time(4)  # their day runs from 4:00 to 4:00, so a 1 am message ends the day before
LEARN_DAYS = 14
LEARN_LEAST = 3  # fewer days than this with a message, and the usual time is the default below
USUAL = {Part.MORNING: time(9), Part.NIGHT: time(22)}
ROUND_TO = 5  # minutes
WROTE_LATELY = timedelta(hours=2)  # a greeting other than a morning one is skipped after this
BACK_OFF = 3  # greetings sent since they last wrote, and the series pauses
ENDED = frozenset({"sent", "late", "expired", "skipped", "cancelled"})
SENT = frozenset({"sent", "late"})


@dataclass(frozen=True, slots=True)
class Planned:
    """A repeating request as read: when it falls, and whether code filled in a vague time."""

    repeat: Repeat
    defaulted: bool = False


@dataclass(frozen=True, slots=True)
class Step:
    """What tending a series comes to: a new state to record (None when it stays, with why), and
    the next occurrence to make, its number and when it falls (None for none)."""

    state: Standing | None = None
    reason: str = ""
    due: datetime | None = None
    seq: int = 0


def _part(s: Slots) -> Part:
    if s.kind is not Kind.GREETING:
        return Part.OTHER
    words = s.thing.lower()
    if s.part == "morning" or "morning" in words:
        return Part.MORNING
    if s.part == "night" or "night" in words:
        return Part.NIGHT
    return Part.OTHER


def _weekday(s: Slots) -> int | str | None:
    """Every day (None), every week on a day (its number), or why to ask how often."""
    if s.every == "day":
        return None
    if s.every in WEEKDAYS:
        return WEEKDAYS.index(s.every)
    if s.every == "unsaid" and s.day == "weekday" and s.weekday in WEEKDAYS:
        return WEEKDAYS.index(s.weekday)
    return HOW_OFTEN


def repeat_of(s: Slots, now: datetime, tz: tzinfo) -> Planned | str:
    """How a repeating request falls, or why to ask. A time they said is kept as said; a morning or
    night greeting with none is learned; a part of the day alone has its fixed hour, said back with
    an offer to change it; anything else with no time asks what time."""
    weekday, part = _weekday(s), _part(s)
    if isinstance(weekday, str):
        return weekday
    if s.hour is None:
        if part is not Part.OTHER:
            return Planned(Repeat(weekday, None, part))
        if s.part in PARTS:
            return Planned(Repeat(weekday, PARTS[s.part], part), defaulted=True)
        return "what time"
    if s.part == "unsaid" and part is not Part.OTHER:
        s = replace(s, part=part.value)
    local = now.astimezone(tz)
    clock = clock_of(s, local, local.date() + timedelta(days=1))  # not today: a bare hour is asked
    return (
        Planned(Repeat(weekday, clock, part)) if isinstance(clock, time) else clock or "what time"
    )


def _day_of(t: datetime, tz: tzinfo) -> date:
    """Their day a moment belongs to, the day starting at DAY_STARTS."""
    start = DAY_STARTS.hour * 60 + DAY_STARTS.minute
    return (t.astimezone(tz) - timedelta(minutes=start)).date()


def usual_time(part: Part, theirs: Sequence[datetime], now: datetime, tz: tzinfo) -> time:
    """When they usually start their day (the first message of each day, a morning) or end it (the
    last, a night): the median over the last LEARN_DAYS days, rounded to ROUND_TO minutes. Today
    counts for a morning once they have written, never for a night, which is not over. Fewer than
    LEARN_LEAST days, and it is the default for the part."""
    today, start = _day_of(now, tz), DAY_STARTS.hour * 60 + DAY_STARTS.minute
    days: dict[date, list[int]] = {}
    for t in theirs:
        day = _day_of(t, tz)
        if not 0 <= (today - day).days < LEARN_DAYS or (part is Part.NIGHT and day == today):
            continue
        local = t.astimezone(tz)
        days.setdefault(day, []).append((local.hour * 60 + local.minute - start) % 1440)
    marks = [min(m) if part is Part.MORNING else max(m) for m in days.values()]
    if len(marks) < LEARN_LEAST:
        return USUAL.get(part, USUAL[Part.MORNING])
    rounded = ROUND_TO * math.floor(median(marks) / ROUND_TO + 0.5)
    minutes = (rounded + start) % 1440
    return time(minutes // 60, minutes % 60)


def next_due(
    repeat: Repeat, clock: time, now: datetime, tz: tzinfo, previous: datetime | None
) -> datetime:
    """The next time a series falls at `clock` wall time in `tz`: after now, and on a later day than
    the one before it, so a learned time that moved later never sends twice in a day."""
    local = now.astimezone(tz)
    day = local.date()
    if previous is not None:
        day = max(day, previous.astimezone(tz).date() + timedelta(days=1))
    if repeat.weekday is not None:
        day += timedelta(days=(repeat.weekday - day.weekday()) % 7)
    at = datetime.combine(day, clock, tzinfo=tz)
    if at <= local:
        at = datetime.combine(day + timedelta(days=1 if repeat.weekday is None else 7), clock, tz)
    return at


def skip_reason(
    series: Series, due: datetime, theirs: Sequence[datetime], now: datetime, tz: tzinfo
) -> str | None:
    """Why a greeting is not sent: they already wrote first, since their day began for a morning
    one, in the WROTE_LATELY before it for any other. A reminder or check-in is never skipped."""
    if series.kind is not Kind.GREETING:
        return None
    if series.repeat.part is Part.MORNING:
        since, why = datetime.combine(_day_of(due, tz), DAY_STARTS, tz), "already wrote today"
    else:
        since, why = due - WROTE_LATELY, "wrote in the two hours before"
    return f"they {why}" if any(since <= t <= now for t in theirs) else None


def standing(kind: Kind, sent: Sequence[datetime], their_last: datetime | None) -> Standing:
    """A greeting sent BACK_OFF times since they last wrote pauses; anything else stays active."""
    if kind is not Kind.GREETING:
        return Standing.ACTIVE
    unanswered = sum(1 for t in sent if their_last is None or t > their_last)
    return Standing.PAUSED if unanswered >= BACK_OFF else Standing.ACTIVE


def tend(
    series: Series, occurrences: Sequence[Reminder], theirs: Sequence[datetime], now: datetime,
    tz: tzinfo,
) -> Step:  # fmt: skip
    """What a series needs now. Nothing while one is pending or being sent, or once stopped.
    Otherwise it pauses or resumes by `standing`, and an active one gets its next occurrence, the
    number after the last, so a second run makes the same one and the store keeps the first."""
    if series.state is Standing.STOPPED or any(o.state not in ENDED for o in occurrences):
        return Step()
    sent = [o.state_at for o in occurrences if o.state in SENT and o.state_at is not None]
    want = standing(series.kind, sent, max(theirs, default=None))
    change, reason = None, ""
    if want is not series.state:
        change = want
        reason = (
            f"{BACK_OFF} sent since they last wrote" if want is Standing.PAUSED else "they wrote"
        )
    if want is Standing.PAUSED:
        return Step(change, reason)
    last = max(occurrences, key=lambda o: o.seq or 0, default=None)
    clock = series.repeat.at or usual_time(series.repeat.part, theirs, now, tz)
    due = next_due(series.repeat, clock, now, tz, last.due_at if last is not None else None)
    return Step(change, reason, due, (last.seq or 0) + 1 if last is not None else 1)


def clock_words(at: time) -> str:
    return f"{at.hour % 12 or 12}:{at.minute:02d} {'am' if at.hour < 12 else 'pm'}"


def how_often(repeat: Repeat) -> str:
    """ "every day", "every Monday": how often it goes, for a note or a list."""
    return "every day" if repeat.weekday is None else f"every {WEEKDAYS[repeat.weekday].title()}"


def every_words(repeat: Repeat) -> str:
    """ "every day at 8:00 am"; a learned one by when they usually start or end their day, never a
    made-up exact time: "every morning, around when they usually start their day"."""
    if repeat.at is not None:
        return f"{how_often(repeat)} at {clock_words(repeat.at)}"
    on = "" if repeat.weekday is None else f" {WEEKDAYS[repeat.weekday].title()}"
    if repeat.part is Part.NIGHT:
        return f"every{on} night, around when they usually end their day"
    return f"every{on} morning, around when they usually start their day"


def first_words(repeat: Repeat, due: datetime, now: datetime, tz: tzinfo) -> str:
    """When the first one goes: as `spoken`, or by the day and part for a learned time."""
    if repeat.at is not None:
        return spoken(due, now, tz)
    local, today = due.astimezone(tz), now.astimezone(tz).date()
    night = repeat.part is Part.NIGHT
    if local.date() == today:
        return "tonight" if night else "this morning"
    day = "tomorrow" if local.date() == today + timedelta(days=1) else local.strftime("%A")
    return f"{day} {'night' if night else 'morning'}"


def repeat_note(kind: Kind, thing: str, planned: Planned, first: str) -> str:
    extra = " Say they can change the time." if planned.defaulted else ""
    if planned.repeat.at is None:
        extra = " Name no clock time for it."
    return REPEAT_NOTE.render(
        what=asked_for(kind, thing), every=every_words(planned.repeat), first=first, extra=extra
    )
