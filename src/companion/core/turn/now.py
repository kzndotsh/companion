"""What is happening with them now (ADR 0024): what they said is coming, kept by code until they say
it happened, they are back, or it is well past its time. A small model labels each message; this
folds the labels into what is still open, and words the note for it. Pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from companion.core.types import Decision, Json, Speaker, Utterance
from companion.prompts import get

KEY = "now: what is happening with them"
PROMPT = get("system/now")
NOTE = get("notes/now-soon")
MINUTES = (5, 180)  # a guess outside this is clamped
KEEPS = (
    timedelta(minutes=20),
    timedelta(hours=3),
)  # an item closes after 3x its minutes, within these
LOOKBACK = KEEPS[1]


class Phase(StrEnum):
    SOON = "soon"  # about to happen while they are still here
    LEAVING = "leaving"  # going now, away for a while
    BACK = "back"
    DONE = "done"  # what they said was coming has happened
    NONE = "none"


OPENS = frozenset({Phase.SOON, Phase.LEAVING})
CLOSES = frozenset({Phase.BACK, Phase.DONE})

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "now": {"type": "string", "enum": [p.value for p in Phase]},
        "what": {"type": "string"},
        "minutes": {"type": "integer"},
    },
    "required": ["now", "what", "minutes"],
}


@dataclass(frozen=True, slots=True)
class Label:
    phase: Phase
    what: str
    minutes: int


@dataclass(frozen=True, slots=True)
class Said:
    """One labelled message of theirs, as logged."""

    label: Label
    text: str
    turn: str
    at: datetime


def parse(data: Json) -> Label | None:
    """The label, minutes clamped; None when it cannot be read. A phase that opens needs a what."""
    if not isinstance(data, dict):
        return None
    phase, what, minutes = data.get("now"), data.get("what"), data.get("minutes")
    if phase not in set(Phase) or not isinstance(what, str):
        return None
    if not isinstance(minutes, int) or isinstance(minutes, bool):
        return None
    label = Label(
        Phase(str(phase)), " ".join(what.split()), max(MINUTES[0], min(MINUTES[1], minutes))
    )
    return None if label.phase in OPENS and not label.what else label


def reader_input(prior: Sequence[Utterance], text: str) -> str:
    """Their message, after the companion's message just before it when there is one, so a short
    answer ("soon lol") reads with what it answers."""
    last = next((u.text for u in reversed(prior) if u.speaker is Speaker.COMPANION), None)
    return (f"COMPANION: {last}\n" if last else "") + f"USER: {text}"


def keeps(label: Label) -> timedelta:
    """How long an item stays open with nothing said: three times its minutes, within bounds."""
    return max(KEEPS[0], min(KEEPS[1], timedelta(minutes=3 * label.minutes)))


def open_now(said: Sequence[Said], now: datetime) -> list[Said]:
    """What is still open, oldest first: each soon or leaving opens one, a back or a done closes
    everything before it, and an item closes once well past its time."""
    out: list[Said] = []
    for s in sorted(said, key=lambda s: s.at):
        if s.label.phase in CLOSES:
            out = []
        elif s.label.phase in OPENS:
            out.append(s)
    return [s for s in out if now - s.at <= keeps(s.label)]


def ago(delta: timedelta) -> str:
    minutes = round(delta.total_seconds() / 60)
    if minutes < 2:
        return "a minute"
    if minutes < 60:
        return f"{minutes} minutes"
    hours = round(minutes / 60)
    return "an hour" if hours == 1 else f"{hours} hours"


def soon_note(said: Sequence[Said], now: datetime) -> str | None:
    """The line after the history for the newest open soon item, or None. A leaving item needs
    none: if they are writing, they are back."""
    soon = [s for s in open_now(said, now) if s.label.phase is Phase.SOON]
    if not soon:
        return None
    s = soon[-1]
    return NOTE.render(ago=ago(now - s.at), what=s.label.what)


def from_decisions(decisions: Sequence[Decision]) -> list[Said]:
    """Their labelled messages from the logged decisions; one that cannot be read is skipped."""
    out: list[Said] = []
    for d in decisions:
        detail = d.detail or {}
        label = parse(
            {
                "now": detail.get("phase"),
                "what": detail.get("what"),
                "minutes": detail.get("minutes"),
            }
        )
        if label is not None:
            out.append(Said(label, str(detail.get("said", "")), str(d.turn_id), d.at))
    return out
