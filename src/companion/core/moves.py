"""Spotting what the companion keeps doing, by reading its own recent replies.

Counting repeated words misses most of it: a pet name, an emoji, an action in asterisks followed by
a quoted line, the same gesture in new words. A small model reads the last few replies and names
what repeats. The note it feeds into the next request only describes the habit and asks for
something different; it never edits a reply. The model's text is bounded in length and count, and
the decision to ask is logged with the scorer, never rendered as a reason by the model (ADR 0006).
"""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.types import Json, Speaker, Utterance

WINDOW = 6
MIN_REPLIES = 4
MAX_HABITS = 3
MAX_HABIT_CHARS = 90
# A habit found on one turn is only used for the next two, so a stale one does not linger.
FRESH_FOR = 2

SYSTEM = """You read the last several replies a companion sent in a chat and name what it keeps \
doing in them. Look for repetition a reader would find stale: the same pet name or word, the same \
emoji, the same sentence shape (for example an action in asterisks and then a quoted line), the \
same gesture or move in different words, the same way of opening or closing, or the same \
reaction. Name at most three, each as a short plain description under 90 characters (for example: \
calls them "sweetheart" in most replies; ends with the same smirking emoji; tucks a hand at their \
waist). Only name something that really repeats in at least three replies. If the replies are \
varied, return an empty list."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "habits": {
            "type": "array",
            "maxItems": MAX_HABITS,
            "items": {"type": "string", "maxLength": MAX_HABIT_CHARS},
        }
    },
    "required": ["habits"],
}


def replies_to_read(prior: Sequence[Utterance], latest: str) -> list[str]:
    """The companion's last few replies, oldest first, ending with the one just sent. None when
    there are too few to judge."""
    mine = [u.text for u in prior if u.speaker is Speaker.COMPANION][-(WINDOW - 1) :]
    replies = [*mine, latest]
    return replies if len(replies) >= MIN_REPLIES else []


def build_prompt(replies: Sequence[str]) -> str:
    return "\n".join(f"[reply {i}] {text}" for i, text in enumerate(replies, start=1))


def parse(data: Json) -> list[str] | None:
    """The habits named, cleaned and bounded, or None if the answer was malformed."""
    raw = data.get("habits") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    habits: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            return None
        text = " ".join(item.split())[:MAX_HABIT_CHARS]
        if text:
            habits.append(text)
    return habits[:MAX_HABITS]


def note_for(habits: Sequence[str]) -> str | None:
    if not habits:
        return None
    return (
        "[Your recent replies keep doing this: " + "; ".join(habits) + ". Do something different.]"
    )
