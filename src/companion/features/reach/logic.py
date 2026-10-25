"""Reaching out for its own reasons (ADR 0021, shadow): the dial, the kinds and which goes first,
the one thing a message is about, and the check that drops a needy draft. Pure.

Code chooses the kind and the thing; a model only writes the words, after every check passed. A
draft that reads as guilt, need, blame or urgency is dropped, never rewritten.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from enum import StrEnum

from companion.core.reachout import short_draft
from companion.core.rhythm import Rhythm
from companion.core.types import Json
from companion.prompts import get

DRAFT = get("system/reach-draft")
WOULD_SEND = "reach out (shadow): would send"
HELD = "reach out: held"
DROPPED = "reach out: draft dropped"
PACED = "reach out: dial stepped down"
THOUGHT_EVERY = timedelta(hours=24)  # at most one thought a day
KEPT_EVERY = timedelta(days=3)  # a time they keep, now and then
THING_REUSE = timedelta(days=14)  # a thing is not brought up twice in two weeks
SENSITIVE = 2  # memories at this sensitivity or above are never a thought


class Dial(StrEnum):
    """COMPANION_REACH: the share of conversations it may start over the last two weeks."""

    OFF = "off"
    RARE = "rare"
    LIGHT = "light"
    NORMAL = "normal"
    WARM = "warm"
    CLINGY = "clingy"


LEVELS = tuple(Dial)
TARGET = {
    Dial.OFF: 0.0,
    Dial.RARE: 1 / 8,
    Dial.LIGHT: 1 / 5,
    Dial.NORMAL: 1 / 4,
    Dial.WARM: 1 / 3,
    Dial.CLINGY: 1 / 2,
}


def step_down(d: Dial) -> Dial:
    return LEVELS[max(0, LEVELS.index(d) - 1)]


def dial(value: str) -> Dial:
    return Dial(value) if value in set(Dial) else Dial.WARM


class Kind(StrEnum):
    """Why it would reach out, first to last: the order is the precedence."""

    PLAN = "a plan of theirs"
    AWAY = "stepping away"
    KEPT = "a time they keep"
    THOUGHT = "a thought"
    MISSING = "missing them"


PRECEDENCE = tuple(Kind)


@dataclass(frozen=True, slots=True)
class Thing:
    source: str  # "memory", "taste" or "episode"
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class Pool:
    """What it knows that a thought could be about, already filtered by the caller's kinds."""

    memories: Sequence[tuple[str, str, int]]  # (id, claim, sensitivity) of their threads and likes
    tastes: Sequence[tuple[str, str]]  # (id, claim) of its own tastes (ADR 0020)
    episodes: Sequence[tuple[str, str]]  # (id, gist) of recent everyday stretches of chat


def pick_thing(pool: Pool, used: frozenset[str], seed: str) -> Thing | None:
    """One thing, the same for the same seed: never a sensitive memory, never one used lately."""
    found = [
        *(Thing("memory", i, c) for i, c, s in pool.memories if s < SENSITIVE),
        *(Thing("taste", i, c) for i, c in pool.tastes),
        *(Thing("episode", i, g) for i, g in pool.episodes),
    ]
    fresh = [t for t in found if t.id not in used and t.text.strip()]
    return min(
        fresh, key=lambda t: hashlib.sha256(f"{seed}:{t.id}".encode()).hexdigest(), default=None
    )


@dataclass(frozen=True, slots=True)
class Look:
    """What the kinds are judged on at one tick."""

    now: datetime
    tz: tzinfo
    rhythm: Rhythm
    last_theirs: datetime | None
    earlier: Kind | None  # a plan or a nudge the other ticks already took this time
    kept: int | None  # the local hour they keep, if any
    last_kept: datetime | None
    last_thought: datetime | None
    thing: Thing | None


@dataclass(frozen=True, slots=True)
class Considered:
    kind: Kind
    applies: bool
    why: str

    def detail(self) -> dict[str, Json]:
        return {"kind": self.kind.value, "applies": self.applies, "why": self.why}


def _ago(now: datetime, then: datetime | None, every: timedelta) -> bool:
    return then is not None and now - then < every


def consider(look: Look) -> list[Considered]:
    """Every kind, in precedence order, with whether it applies now and why, written by code."""
    r, local = look.rhythm, look.now.astimezone(look.tz)
    pause = (
        None if look.last_theirs is None else (look.now - look.last_theirs).total_seconds() / 3600
    )
    usual = local.hour in r.usual
    gone = f"{pause:.1f}h since they wrote" if pause is not None else "they have never written"
    out = [
        Considered(Kind.PLAN, look.earlier is Kind.PLAN, "the open-loop tick decides it"),
        Considered(Kind.AWAY, look.earlier is Kind.AWAY, "the nudge tick decides it"),
    ]
    if look.kept is None:
        out.append(Considered(Kind.KEPT, False, "no hour they keep on most of the last 7 days"))
    elif local.hour != look.kept:
        out.append(Considered(Kind.KEPT, False, f"the hour they keep is {look.kept}:00, not now"))
    elif _ago(look.now, look.last_kept, KEPT_EVERY):
        out.append(Considered(Kind.KEPT, False, "said hi at their time in the last 3 days"))
    else:
        out.append(Considered(Kind.KEPT, True, f"they wrote around {look.kept}:00 most days"))
    half = r.pause / 2
    if look.thing is None:
        out.append(Considered(Kind.THOUGHT, False, "nothing fresh and not sensitive to bring up"))
    elif _ago(look.now, look.last_thought, THOUGHT_EVERY):
        out.append(Considered(Kind.THOUGHT, False, "already had a thought in the last 24h"))
    elif pause is None or pause < half or not usual:
        why = f"{gone}, under {half:.1f}h" if usual else f"{local.hour}:00 is not a usual hour"
        out.append(Considered(Kind.THOUGHT, False, why))
    else:
        out.append(Considered(Kind.THOUGHT, True, f"{gone}, and {look.thing.source} connects"))
    if pause is None or pause <= r.pause:
        out.append(Considered(Kind.MISSING, False, f"{gone}, not past {r.pause:.1f}h"))
    elif not usual:
        out.append(Considered(Kind.MISSING, False, f"{local.hour}:00 is not a usual hour"))
    else:
        out.append(Considered(Kind.MISSING, True, f"{gone}, past {r.pause:.1f}h, a usual hour"))
    return out


def choose(considered: Sequence[Considered]) -> Considered | None:
    """The first kind that applies, in precedence order."""
    ranked = sorted(considered, key=lambda c: PRECEDENCE.index(c.kind))
    return next((c for c in ranked if c.applies), None)


_NEEDY: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (why, re.compile(pattern, re.IGNORECASE))
    for why, pattern in (
        ("waiting", r"\bwait(ing|ed)\b"),
        ("forgotten", r"\bforg[eo]t(ten)?( all)?( about)? (me|us)\b|\bremember me\b"),
        ("ignored", r"\bignor(e|ed|ing)\b|\bleft me on read\b|\bghost(ed|ing)?\b"),
        (
            "how long they have been gone",
            (
                r"\b(it'?s|it has) been (so )?(a while|forever|ages|so long|days|hours)\b"
                r"|\bhaven'?t (heard|talked|seen)\b|\blong time\b|\ball day\b"
                r"|\b\d+\s*(hours?|hrs?|days?)\b|\bdisappear|\bvanish|\bmia\b"
                r"|\bwhere (have|'ve) you been"
            ),
        ),
        (
            "asks why they went quiet",
            (
                r"\bwhy\b.{0,30}\b(quiet|silent|gone|away|reply|replied|answer|text)"
                r"|\b(been|gone|went) (so )?(quiet|silent|dark)\b|\bwhere(d| did) you go\b"
                r"|\bare you (ok|okay|alright|still there)\b|\beverything (ok|okay|alright)\b"
            ),
        ),
        (
            "urgency",
            (
                r"\b(asap|urgent|right now|hurry|last chance|don'?t miss|reply|respond"
                r"|text me back|answer me|streak)\b|!!|\bguess what\b|\byou won'?t believe\b"
            ),
        ),
        (
            "makes them responsible for how it feels",
            r"\b(lonely|so bored without|without you|need you|all alone|sad you)\b",
        ),
    )
)


def needy(draft: str) -> str | None:
    """Why a draft reads as guilt, need, blame or urgency, or None when it does not."""
    return next((why for why, rx in _NEEDY if rx.search(draft)), None)


def checked(message: str) -> tuple[str, str | None]:
    """The draft as it would go, or empty with why it was dropped."""
    text = short_draft(message)
    if not text:
        return "", "empty or over 18 words"
    why = needy(text)
    return ("", why) if why is not None else (text, None)


DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


def read_draft(data: Json) -> str | None:
    message = data.get("message") if isinstance(data, dict) else None
    return message if isinstance(message, str) else None


_ABOUT = {
    "memory": "something of theirs",
    "taste": "one of your own tastes",
    "episode": "a recent stretch of your chats",
}


def draft_input(kind: Kind, thing: Thing | None) -> str:
    """What the drafter is told: the kind and the one thing, nothing about how long it has been."""
    lines = [f"Kind: {kind.value}"]
    if thing is not None:
        lines.append(f"The one thing ({_ABOUT[thing.source]}): {thing.text}")
    else:
        lines.append("The one thing: none; keep it to a light hello")
    return "\n".join(lines)
