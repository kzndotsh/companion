"""Reminders, check-ins and greetings they ask for: "remind me at 8pm to take the dog out", "check
up on me in a few days about the interview", "tell me good morning every day".

A small model reads the request into slots (what, the day words, the time words, whether am or pm
was said); code turns the slots into a time in their zone with fixed rules, and asks instead of
guessing when the time is unclear ("at 8" in the morning, "next friday", a time already past). A
repeating one is a series: every day or every week on one day, at the time they said or, for a
greeting with no time, a time learned from when they usually start or end their day. The model
never sets the clock. No benchmark covers this kind of phrase, so the rules are plain and
tested here, and the reading is tested on made-up phrases (`tests/live`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum
from random import Random

from companion.core.types import Json, RelationshipId, Speaker, TurnId, Utterance
from companion.prompts import get

PROMPT = get("system/reminder-read")
FURTHEST = timedelta(days=60)
A_FEW_DAYS = 3
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
PARTS = {"morning": time(9), "afternoon": time(15), "evening": time(18), "night": time(20)}
# A check-in with no time lands at a time picked once between these, as a friend's would; the reply
# names only the part of the day
WINDOW = (time(16), time(20))
SLOT = timedelta(minutes=5)
SOON = timedelta(minutes=30)  # a check-in picked for today is at least this far off
GRACE = timedelta(hours=2)  # a reminder this late still goes out, marked late; later it expires


class Kind(StrEnum):
    REMINDER = "reminder"
    CHECK_IN = "check_in"
    GREETING = "greeting"  # a ritual message they ask for: "say goodnight every night"


# How often a repeating one goes: every day, every week on a weekday, or something else, which is
# asked about. Optional in the schema, so an answer without it reads as before.
EVERY = ("unsaid", "day", *WEEKDAYS, "other")


class Ask(StrEnum):
    """What a message asks of the reminders."""

    NONE = "none"
    SET = "set"
    CANCEL = "cancel"


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "ask": {"type": "string", "enum": [a.value for a in Ask]},
        "kind": {"type": "string", "enum": [k.value for k in Kind]},
        "thing": {"type": "string"},
        "day": {
            "type": "string",
            "enum": ["unsaid", "today", "tonight", "tomorrow", "in_days", "weekday", "date"],
        },
        "days": {"type": ["integer", "null"]},
        "weekday": {"type": "string"},
        "next_said": {"type": "boolean"},
        "on_date": {"type": "string"},
        "hour": {"type": ["integer", "null"]},
        "minute": {"type": ["integer", "null"]},
        "ampm": {"type": "string", "enum": ["am", "pm", "unsaid"]},
        "part": {"type": "string", "enum": ["morning", "afternoon", "evening", "night", "unsaid"]},
        "in_minutes": {"type": ["integer", "null"]},
        "repeats": {"type": "boolean"},
        "every": {"type": "string", "enum": list(EVERY)},
    },
    "required": ["ask", "kind", "thing", "day", "ampm", "part", "repeats"],
}


@dataclass(frozen=True, slots=True)
class Slots:
    """A request as read: their words for the thing and the parts of when, nothing resolved."""

    ask: Ask
    kind: Kind
    thing: str
    day: str = "unsaid"
    days: int | None = None
    weekday: str = ""
    next_said: bool = False
    on_date: str = ""
    hour: int | None = None
    minute: int = 0
    ampm: str = "unsaid"
    part: str = "unsaid"
    in_minutes: int | None = None
    repeats: bool = False
    every: str = "unsaid"


@dataclass(frozen=True, slots=True)
class When:
    """A resolved time, or why it needs asking about."""

    at: datetime | None
    unclear: str = ""  # a plain reason to ask, empty when `at` is set
    defaulted: bool = (
        False  # a vague time code filled in ("in a few days"): say it and offer a change
    )
    loose: bool = (
        False  # a time picked in the check-in window: say the part of the day, not the minute
    )


def _int(v: Json) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def parse(data: Json) -> Slots | None:
    if not isinstance(data, dict):
        return None
    ask, kind, thing = data.get("ask"), data.get("kind"), data.get("thing")
    if ask not in set(Ask) or kind not in set(Kind) or not isinstance(thing, str):
        return None
    fields: dict[str, Json] = data

    def text(k: str) -> str:
        v = fields.get(k)
        return v if isinstance(v, str) else ""

    every = text("every").lower() or "unsaid"
    return Slots(
        Ask(str(ask)),
        Kind(str(kind)),
        thing.strip(),
        day=text("day") or "unsaid",
        days=_int(data.get("days")),
        weekday=text("weekday").lower(),
        next_said=data.get("next_said") is True,
        on_date=text("on_date"),
        hour=_int(data.get("hour")),
        minute=_int(data.get("minute")) or 0,
        ampm=text("ampm") or "unsaid",
        part=text("part") or "unsaid",
        in_minutes=_int(data.get("in_minutes")),
        repeats=data.get("repeats") is True,
        every=every if every in EVERY else "other",
    )


# Midnight said in so many words. A reader that writes hour 0 for "no time given" (one model did
# for "this evening" and "later", judge bake-off 2026-10-25) would set a midnight reminder.
_MIDNIGHT = re.compile(r"\bmidnight\b|\b12\s*a\.?m\b|\b00[:.]\d\d\b|\b0:\d\d\b", re.IGNORECASE)


def trusted(s: Slots, said: str) -> Slots:
    """The reading with hour 0 kept only when their words say midnight; otherwise no hour, so the
    part of the day they named decides, or it asks."""
    if s.hour == 0 and not _MIDNIGHT.search(said):
        return replace(s, hour=None, minute=0)
    return s


def _day(s: Slots, today: date) -> date | str:  # noqa: PLR0911
    """The calendar day, or why it is unclear."""
    if s.day in ("unsaid", "today", "tonight"):
        return today
    if s.day == "tomorrow":
        return today + timedelta(days=1)
    if s.day == "in_days":
        return today + timedelta(days=s.days if s.days is not None else A_FEW_DAYS)
    if s.day == "weekday":
        if s.weekday not in WEEKDAYS:
            return "which day they meant"
        if s.next_said:
            return f"whether they meant this {s.weekday} or the one after"
        ahead = (WEEKDAYS.index(s.weekday) - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)
    if s.day == "date":
        try:
            return date.fromisoformat(s.on_date)
        except ValueError:
            return "which date they meant"
    return "which day they meant"


def clock_of(s: Slots, now: datetime, day: date) -> time | str | None:  # noqa: PLR0911
    """The time of day, why it is unclear, or None for a check-in left to the window. A bare hour is
    read as the next one still to come, and asked about only when both the morning and the evening
    one are still ahead today."""
    if s.hour is None:
        if s.part in PARTS:
            return PARTS[s.part]
        if s.day == "tonight":
            return PARTS["night"]
        if s.kind is Kind.CHECK_IN:
            return None
        return "what time"
    if not 0 <= s.hour <= 23 or not 0 <= s.minute <= 59:
        return "what time"
    hour = s.hour
    if hour <= 12 and s.ampm in ("am", "pm"):
        hour = hour % 12 + (12 if s.ampm == "pm" else 0)
    elif 1 <= hour <= 11:
        evening = s.part in ("evening", "night", "afternoon") or s.day == "tonight"
        if evening or s.part == "morning":
            hour += 12 if evening else 0
        elif day == now.date():
            am, pm = time(hour, s.minute), time(hour + 12, s.minute)
            if am > now.time():
                return f"whether they meant {hour} in the morning or the evening"
            hour = pm.hour
        else:
            return f"whether they meant {hour} in the morning or the evening"
    return time(hour, s.minute)


def _in_window(s: Slots, day: date, local: datetime, rng: Random) -> datetime:
    """A five-minute slot in the check-in window, at least SOON from now. A check-in with no day
    whose window has gone today moves to tomorrow's."""
    tz = local.tzinfo
    start, end = (datetime.combine(day, t, tzinfo=tz) for t in WINDOW)
    slots = [start + SLOT * i for i in range(int((end - start) / SLOT) + 1)]
    ahead = [x for x in slots if x >= local + SOON]
    if not ahead and s.day == "unsaid":
        ahead = [x + timedelta(days=1) for x in slots]
    return rng.choice(ahead or slots)


def resolve(s: Slots, now: datetime, tz: tzinfo, rng: Random | None = None) -> When:
    """When a request falls, in their zone, or why to ask. Nothing in the past, nothing more than
    sixty days out."""
    local = now.astimezone(tz)
    loose = False
    if s.in_minutes is not None and s.in_minutes > 0:
        at = local + timedelta(minutes=s.in_minutes)
    else:
        day = _day(s, local.date())
        if isinstance(day, str):
            return When(None, day)
        clock = clock_of(s, local, day)
        if isinstance(clock, str):
            return When(None, clock)
        if clock is None:
            at, loose = _in_window(s, day, local, rng or Random()), True  # noqa: S311  a time of day, not a secret
        else:
            at = datetime.combine(day, clock, tzinfo=tz)
            if s.day == "unsaid" and at <= local:
                at += timedelta(days=1)  # "at 9am" said after nine means tomorrow
    if at <= local:
        return When(None, "that time has already passed")
    if at - local > FURTHEST:
        return When(None, "that is further out than reminders go (sixty days)")
    vague = (s.day == "in_days" and s.days is None) or (s.hour is None and s.in_minutes is None)
    return When(at, defaulted=vague, loose=loose)


def spoken(at: datetime, now: datetime, tz: tzinfo, *, loose: bool = False) -> str:
    """The time as a person would say it back: "tonight at 8:00 pm", "tomorrow at 9:00 am",
    "Friday 24 Oct at 6:00 pm"; a loose one by the part of the day: "Thursday evening"."""
    local, today = at.astimezone(tz), now.astimezone(tz).date()
    if loose:
        part = "afternoon" if local.hour < 17 else "evening"
        if local.date() == today:
            return f"this {part}"
        if local.date() == today + timedelta(days=1):
            return f"tomorrow {part}"
        return f"{local.strftime('%A')} {part}"
    clock = local.strftime("%I:%M %p").lstrip("0").lower()
    if local.date() == today:
        return f"{'tonight' if local.hour >= 18 else 'today'} at {clock}"
    if local.date() == today + timedelta(days=1):
        return f"tomorrow at {clock}"
    return f"{local.strftime('%A %d %b')} at {clock}"


_WORDS = re.compile(
    r"\b(remind|reminder|reminders|check (?:up |back )?(?:on|in with) me|check in on me|ping me"
    r"|nudge me|text me|message me|don'?t let me forget|make sure i|ask me (?:how|about|later)"
    r"|tell me (?:at|in|when|tomorrow|tonight))\b",
    re.IGNORECASE,
)
ASKED_WHEN = "reminders: asked them when"
CONTEXT = 4
SET_NOTE, ASK_NOTE, CANCELLED_NOTE = (
    get("notes/reminder-set"),
    get("notes/reminder-ask"),
    get("notes/reminder-cancelled"),
)
SEND, GREETING_SEND = get("system/reminder-send"), get("system/greeting-send")
ONE_OFF = "only one-off reminders can be set for now, so offer to set just the next one"


def likely(said: str, *, asked_when: bool) -> bool:
    """Whether to read the message at all: reminder words, or the answer to its asking when."""
    return asked_when or _WORDS.search(said) is not None


def read_prompt(prior: Sequence[Utterance], said: str, now: datetime, tz: tzinfo) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in prior[-CONTEXT:]
    ]
    stamp = now.astimezone(tz).strftime("%A %d %B %Y, %H:%M")
    return "\n".join(
        [f"It is now {stamp}.", "Conversation:", *lines, "", f"Newest USER message: {said}"]
    )


_FILLER = {
    "the", "that", "this", "thing", "one", "reminder", "reminders", "about", "and", "for", "you",
    "it's", "good", "every", "daily", "saying",
}  # fmt: skip


def _words(text: str) -> set[str]:
    """The words a cancel is matched on: "goodnight" and "good night" both come to "night"."""
    found = {w.removeprefix("good") or w for w in re.findall(r"[a-z']+", text.lower())}
    return {w for w in found if len(w) >= 3} - _FILLER


def matching(pending: Sequence[tuple[str, str]], thing: str) -> list[str]:
    """Which pending reminders or series (id, thing) a cancel names: those sharing a word with what
    they said (filler words aside), or the only one when nothing is named."""
    said = _words(thing)
    hits = [rid for rid, t in pending if said & _words(t)]
    if hits:
        return hits
    return [pending[0][0]] if len(pending) == 1 else []


def asked_for(kind: Kind, thing: str) -> str:
    """What they asked it to do, for a note: "remind them about the dog", "say goodnight to
    them"."""
    return f"say {thing} to them" if kind is Kind.GREETING else f"remind them about {thing}"


def set_note(kind: Kind, thing: str, when: str, *, defaulted: bool) -> str:
    extra = " Say they can change the time." if defaulted else ""
    return SET_NOTE.render(what=asked_for(kind, thing), when=when, extra=extra)


def ask_note(kind: Kind, thing: str, reason: str) -> str:
    return ASK_NOTE.render(what=asked_for(kind, thing), reason=reason)


def cancelled_note(what: str) -> str:
    """`what` is each dropped one as `asked_for` says it, a series with how often it went."""
    return CANCELLED_NOTE.render(what=what)


def send_instruction(kind: Kind, thing: str) -> str:
    if kind is Kind.GREETING:
        return GREETING_SEND.render(what=thing)
    what = (
        f"check in on how {thing} went" if kind is Kind.CHECK_IN else f"remind them about {thing}"
    )
    return SEND.render(what=what)


def sent_with(kind: Kind) -> str:
    """The `name@version` of the prompt a due one of this kind is written with."""
    return (GREETING_SEND if kind is Kind.GREETING else SEND).ref


def plain(kind: Kind, thing: str) -> str:
    """What goes out when the talker cannot write it: their words, marked."""
    if kind is Kind.GREETING:
        return thing
    return f"⏰ {thing}" if kind is Kind.REMINDER else f"hey, how did {thing} go?"


# Repeating ones. A series is the standing request; each time it falls is an ordinary reminder row
# with the series' id and its number in it, made once the one before has ended.


class Part(StrEnum):
    """The part of the day a greeting belongs to. A morning or night greeting with no time said
    goes at a time learned from when they usually start or end their day, and is skipped by its own
    rule; anything else has a time they said."""

    MORNING = "morning"
    NIGHT = "night"
    OTHER = "other"


class Standing(StrEnum):
    """A series' state, its newest event."""

    ACTIVE = "active"
    PAUSED = "paused"  # greetings nobody answered; it resumes when they write
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class Repeat:
    """When a series falls: every day, or every week on `weekday` (Monday 0), at the wall time
    they said, or with `at` None at a time learned for `part` (morning or night)."""

    weekday: int | None
    at: time | None
    part: Part = Part.OTHER

    @property
    def rule(self) -> str:
        return "daily" if self.weekday is None else "weekly"


@dataclass(frozen=True, slots=True)
class Reminder:
    """One reminder: a one-off, or one occurrence of a series (`series_id`, its number `seq`).
    Its state is its newest event, which happened at `state_at`."""

    id: str
    relationship_id: RelationshipId
    kind: Kind
    thing: str
    quote: str
    due_at: datetime
    local_wall: str
    zone: str
    turn_id: TurnId
    created_at: datetime
    state: str = "pending"
    series_id: str | None = None
    seq: int | None = None
    state_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Series:
    id: str
    relationship_id: RelationshipId
    kind: Kind
    thing: str
    quote: str
    repeat: Repeat
    zone: str
    turn_id: TurnId
    created_at: datetime
    state: Standing = Standing.ACTIVE
