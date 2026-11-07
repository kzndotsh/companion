"""What every reach-out shares, whatever prompted it: a hold from the shared gate (`Held`, ADR
0023), the answer a drafting judge gives and how a draft is tidied, and the check that drops a
needy one. Pure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import cast

from companion.core.types import Json, RelationshipId


class Mode(StrEnum):
    """What became of a reach-out. The strings are stored in the reach-out tables."""

    SHADOW = "shadow"  # drafted and checked, never sent
    LIVE = "live"  # sent
    DROPPED = "dropped"  # failed the check, so nothing was drafted to send


@dataclass(frozen=True, slots=True)
class ReachOut:
    """A reach-out about a plan, as its table `reach_outs` keeps it: written by threads. Read it
    with every other kind as a `ReachRecord`."""

    id: str
    relationship_id: RelationshipId
    loop_id: str
    mode: Mode
    draft: str
    reason: str
    at: datetime


@dataclass(frozen=True, slots=True)
class ReachRecord:
    """One reach-out of any kind, however it was stored (a plan's row, its own reasons' row, or a
    nudge's decision): what the pacing, the outcomes and `companion initiative` read. `detail`
    holds what is particular to the kind, the way its writer stored it."""

    id: str
    kind: Kind
    mode: Mode
    text: str
    at: datetime
    thing: str = ""  # what it was about (its own reasons), an id, or empty
    detail: dict[str, Json] = field(default_factory=dict[str, Json])

    @property
    def live(self) -> bool:
        return self.mode is Mode.LIVE


# The decision keys of the three kinds of reach-out, each named here once because readers (the
# pacing, `companion initiative`) mean all of them. The strings are stored in the decision log, so
# they stay as they are. A hold is a reach-out the gate held back; a would-send is a shadow one.
PLAN_HELD = "held, would otherwise reach out"  # about a plan (features/threads)
OWN_HELD = "reach out: held"  # for its own reasons (features/reach)
HELD_KEYS = (PLAN_HELD, OWN_HELD)
PLAN_WOULD_SEND = "shadow, would send"
OWN_WOULD_SEND = "reach out (shadow): would send"
WOULD_NUDGE = "nudge (shadow): would send"  # after they stepped away (features/nudges)


class Kind(StrEnum):
    """Why it would reach out, first to last: the order is the precedence, stated here once. The
    initiative timer runs the features that can take a tick in this order (`kit/features.py`
    `Reaching`)."""

    PLAN = "a plan of theirs"
    AWAY = "stepping away"
    KEPT = "a time they keep"
    THOUGHT = "a thought"
    MISSING = "missing them"


PRECEDENCE = tuple(Kind)
OWN_KINDS = frozenset({Kind.KEPT, Kind.THOUGHT, Kind.MISSING})  # its own reasons (features/reach)


class Dial(StrEnum):
    """COMPANION_REACH: the share of conversations it may start over the last two weeks."""

    OFF = "off"
    RARE = "rare"
    LIGHT = "light"
    NORMAL = "normal"
    WARM = "warm"
    CLINGY = "clingy"


DEFAULT_DIAL = Dial.WARM


def dial(value: object, fallback: Dial = DEFAULT_DIAL) -> Dial:
    """The dial a setting or a record names; `fallback` for anything that is not one."""
    return Dial(value) if isinstance(value, str) and value in set(Dial) else fallback


@dataclass(frozen=True, slots=True)
class Held:
    """The shared gate's hold on any reach-out (ADR 0023): which hold, the same from tick to tick,
    and the reason with its numbers."""

    what: str
    why: str


# What every drafting judge is asked for and answers: one message.
DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


def parse_draft(data: Json) -> str | None:
    """The message a drafting judge wrote, as it wrote it; None for an answer without one."""
    message = data.get("message") if isinstance(data, dict) else None
    return message if isinstance(message, str) else None


def draft_text(message: str) -> str:
    """The draft as the model wrote it, spacing tidied; empty when it wrote nothing. A long draft is
    neither cut nor dropped: the drafting prompts ask for a short message, and code never edits
    one (the owner's choice, 2026-10-25; before, a draft over 18 words was cut to its first
    sentence when that was a question, else dropped). Two ways a model's answer arrives broken are
    undone, since they are transport, not words: the whole answer wrapped again as JSON
    (`{"message": ...}` inside the field, 3 of 5 shadow drafts by 2026-11-02), and UTF-8 read as
    cp1252 (an emoji arriving as a run of accented Latin letters)."""
    return " ".join(_unmangled(_unwrapped(message)).split())


def _unwrapped(message: str) -> str:
    try:
        inner = json.loads(message)
    except ValueError:
        return message
    if not isinstance(inner, dict):
        return message
    got = cast("dict[str, object]", inner).get("message")
    return got if isinstance(got, str) else message


_MOJIBAKE = re.compile("[ÃÂâð][\u0080-¿Œ-™]")


def _unmangled(message: str) -> str:
    if not _MOJIBAKE.search(message):
        return message
    try:
        return message.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return message


def garbled(text: str) -> bool:
    """Whether mis-decoded bytes are left that could not be undone."""
    return _MOJIBAKE.search(text) is not None


# A draft that reads as guilt, need, blame or urgency is dropped, never rewritten (ADR 0021). Every
# reach-out's draft is checked: its own reasons, a plan of theirs and a nudge.
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


def drafted(message: str | None, missing: str) -> tuple[str, str | None]:
    """`checked`, for a drafting call that may have given no message at all (`missing` says why):
    the draft as it would go, or empty with why it was dropped."""
    return ("", missing) if message is None else checked(message)


def checked(message: str) -> tuple[str, str | None]:
    """The draft as it would go, or empty with why it was dropped."""
    text = draft_text(message)
    if not text:
        return "", "empty"
    if garbled(text):
        return "", "garbled text"
    why = needy(text)
    return ("", why) if why is not None else (text, None)
