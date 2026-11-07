"""What every reach-out shares, whatever prompted it: a hold from the shared gate (`Held`, ADR
0023), the answer a drafting judge gives and how a draft is tidied, and the check that drops a
needy one. Pure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import cast

from companion.core.types import Json

# The key of a nudge it would send (features/nudges), read by any reach-out that counts its own.
WOULD_NUDGE = "nudge (shadow): would send"


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


def checked(message: str) -> tuple[str, str | None]:
    """The draft as it would go, or empty with why it was dropped."""
    text = draft_text(message)
    if not text:
        return "", "empty"
    if garbled(text):
        return "", "garbled text"
    why = needy(text)
    return ("", why) if why is not None else (text, None)
