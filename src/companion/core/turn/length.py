"""How long to answer: the one place a length target is chosen, never by a model (ADR 0014).

On short, casual statements the replies ran three to four times longer than the message they
answered (a 4-word message got a median of 15 words; see `evals/CHANGELOG.md`). When they wrote a
lot, or asked something, the length was already about right, so a short statement is the only
everyday case with a target. A serious message gets a fixed target that used to sit inside the
serious listening note (35 words, measured there). An acute message, a scene and a question
(with or without its question mark) get none: a short "i want to die" must never be answered
under a word cap.

The target for a short statement varies a little each turn, seeded by the turn, so replies are not
all the same size and a replay still rebuilds the same note. The note rides in the system block
with the clock, never in their message, and only this module puts a number of words in front of
the model.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass

from companion.prompts import get

MAX_USER_WORDS = 12
FLOOR_WORDS = 8
MIN_VARIED_WORDS = 5
VARY = (0.6, 1.5)  # the range a short statement's target is scaled by, per turn
SERIOUS_WORDS = 35
SERIOUS, ACUTE = 2, 3  # listening severities
# A short message that asks it something without a question mark: "what about you", "ask me
# something", "and you". Capped like a statement, the reply answered and stopped (flags 2026-10-25).
_ASKS = re.compile(
    r"^\W*(?:(?:ok|okay|so|and|now|then|hmm+)\W+)?(what|how|why|who|where|when|which|wbu|hbu"
    r"|do you|did you|are you|have you|would you|could you|can you|will you|ask me|tell me)\b"
    r"|\b(about you|and you|you\?)\W*$",
    re.IGNORECASE,
)
_NOTE = get("notes/length")
_SERIOUS_NOTE = get("notes/length-serious")


@dataclass(frozen=True, slots=True)
class LengthTarget:
    words: int
    why: str  # for the decision log, written by code
    note: str


def reply_limit(user_words: int) -> int:
    """About one and a half times what they wrote, plus a little, never below a floor."""
    return max(FLOOR_WORDS, math.ceil(1.5 * user_words) + 4)


def varied(base: int, seed: str) -> int:
    """The base scaled by a factor drawn from the seed. No seed means no variation."""
    if not seed:
        return base
    factor = random.Random(seed).uniform(*VARY)  # noqa: S311 - not security, only variety
    return max(MIN_VARIED_WORDS, round(base * factor))


def length_target(
    user_text: str, *, severity: int | None = None, in_scene: bool = False, seed: str = ""
) -> LengthTarget | None:
    """The one length target for this turn, or None when nothing should cap it."""
    if in_scene or (severity is not None and severity >= ACUTE):
        return None
    if severity is not None and severity >= SERIOUS:
        note = _SERIOUS_NOTE.render(limit=SERIOUS_WORDS)
        return LengthTarget(SERIOUS_WORDS, "serious message", note)
    words = len(user_text.split())
    if words == 0 or words > MAX_USER_WORDS or "?" in user_text or _ASKS.search(user_text):
        return None
    base = reply_limit(words)
    limit = varied(base, seed)
    unit = "word" if words == 1 else "words"
    why = f"short statement of {words} {unit}, base {base}"
    return LengthTarget(limit, why, _NOTE.render(words=words, unit=unit, limit=limit))
