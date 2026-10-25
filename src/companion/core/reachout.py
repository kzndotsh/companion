"""What every reach-out shares, whatever prompted it: a hold from the shared gate (`Held`, ADR
0023), how a draft is tidied, and the check that drops a needy one. Pure."""

from __future__ import annotations

import re
from dataclasses import dataclass

# The key of a nudge it would send (features/nudges), read by any reach-out that counts its own.
WOULD_NUDGE = "nudge (shadow): would send"


@dataclass(frozen=True, slots=True)
class Held:
    """The shared gate's hold on any reach-out (ADR 0023): which hold, the same from tick to tick,
    and the reason with its numbers."""

    what: str
    why: str


def draft_text(message: str) -> str:
    """The draft as the model wrote it, spacing tidied; empty when it wrote nothing. A long draft is
    neither cut nor dropped: the drafting prompts ask for a short message, and code never edits
    one (the owner's choice, 2026-10-25; before, a draft over 18 words was cut to its first
    sentence when that was a question, else dropped)."""
    return " ".join(message.split())


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
    why = needy(text)
    return ("", why) if why is not None else (text, None)
