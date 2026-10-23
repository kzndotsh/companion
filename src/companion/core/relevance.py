"""Which memories bear on what they just said (shadow).

The card holds fifteen memories a turn out of well over a hundred, ranked by kind and recency, so
most of what it knows never reaches the reply unless they ask it to remember. This works out, per
turn, which memories bear on the moment: an embedding of their message finds the nearest memories,
then a small model picks at most three of those, or none. Both answers are only logged for now,
with whether each was already on the card, so the two can be compared before either is used.
"""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.frames import is_assertable
from companion.core.types import Belief, Json
from companion.prompts import get

PROMPT = get("system/relevance")
SHADOW = "relevance: what it would have kept in mind (shadow)"
LIVE = "relevance: what it was shown"
GATE = 0.42  # live: the small model picks only when the closest memory is this near (1 turn in 5)
SHOWN = 2  # live: at most this many picks reach the talker, none already on the card
MAX_PICKS = 3
MAX_SENSITIVITY = 2  # never a crisis-level memory on its own
HELD = 2  # held memories only on a turn where they share something, as on the card

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"labels": {"type": "array", "items": {"type": "string"}}},
    "required": ["labels"],
}


def eligible(beliefs: Sequence[Belief], *, sharing: bool) -> list[Belief]:
    """What may be looked up this turn: stated for real, never crisis-level, and held (sensitive)
    memories only when they are sharing something, the same rule as the card."""
    top = MAX_SENSITIVITY if sharing else HELD - 1
    return [b for b in beliefs if is_assertable(b) and b.sensitivity <= top]


def build_prompt(last_reply: str | None, said: str, shortlist: Sequence[Belief]) -> str:
    lines = [f"[r{i}] {b.claim}" for i, b in enumerate(shortlist, start=1)]
    before = [f"COMPANION: {last_reply}"] if last_reply else []
    return "\n".join([*before, f"USER: {said}", "", "What you know:", *lines])


def parse(data: Json, shortlist: Sequence[Belief]) -> list[Belief]:
    """The memories picked, in order, only from labels that were shown, at most three."""
    labelled = {f"r{i}": b for i, b in enumerate(shortlist, start=1)}
    raw = data.get("labels") if isinstance(data, dict) else None
    picked: list[Belief] = []
    for label in raw if isinstance(raw, list) else []:
        b = labelled.get(str(label).strip().strip("[]").strip())
        if b is not None and b not in picked:
            picked.append(b)
    return picked[:MAX_PICKS]


__all__ = [
    "MAX_PICKS",
    "PROMPT",
    "SCHEMA",
    "SHADOW",
    "build_prompt",
    "eligible",
    "parse",
]
