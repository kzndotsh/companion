"""What the talker sees of the past. Live and replay must use these same two rules."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from companion.core.prompt.request import Message
from companion.core.types import Speaker, Utterance
from companion.prompts import get

HISTORY_LIMIT = 40
# A pause this long gets a line in the history saying how much later the next message came. Without
# times the history reads as one stretch: a reminder sent 30 minutes after it was asked for read as
# sent at once. A time on every message was copied into replies (52 of 140); a line only after a
# pause was copied 0 of 140 (evals/CHANGELOG.md, 2026-10-26).
GAP = timedelta(minutes=20)


def gap_line(before: datetime, after: datetime) -> str | None:
    """The history's line between two messages a pause apart, in the machine's local time as the
    clock line is, or None for an ordinary pause. Fixed wall times, never "ago", so the history
    reads the same on every later turn."""
    if after - before < GAP:
        return None
    a, b = before.astimezone(), after.astimezone()
    days = (b.date() - a.date()).days
    minutes = int((after - before).total_seconds() // 60)
    if days == 1:
        when = "the next day"
    elif days > 1:
        when = f"{days} days later"
    elif minutes < 120:
        when = f"{minutes} minutes later"
    else:
        when = f"{minutes // 60} hours later"
    stamp = f"{b:%a} {b.day} {b:%b}, {b.hour % 12 or 12}:{b:%M} {'am' if b.hour < 12 else 'pm'}"
    return get("notes/history-gap").render(when=when, stamp=stamp)


def to_messages(utterances: Sequence[Utterance], now: datetime | None = None) -> list[Message]:
    """The history as messages, with a system line wherever a pause of `GAP` or more came between
    two of them, and before the message now being answered when it came that long after the last
    (`now` is when it came)."""
    out: list[Message] = []
    for n, u in enumerate(utterances):
        line = gap_line(utterances[n - 1].at, u.at) if n else None
        if line is not None:
            out.append(Message("system", line))
        out.append(Message("user" if u.speaker is Speaker.USER else "assistant", u.text))
    last = gap_line(utterances[-1].at, now) if utterances and now is not None else None
    return [*out, Message("system", last)] if last is not None else out
