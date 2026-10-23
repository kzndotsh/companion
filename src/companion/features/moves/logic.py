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
from companion.prompts import get

WINDOW = 6
MIN_REPLIES = 4
# A habit counts only if the model says it appears in at least this many of the replies it read.
MIN_SEEN_IN = 3
MAX_HABITS = 3
MAX_HABIT_CHARS = 90
# A habit found on one turn is only used for the next two, so a stale one does not linger.
FRESH_FOR = 2

PROMPT = get("system/habits")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "habits": {
            "type": "array",
            "maxItems": MAX_HABITS,
            "items": {
                "type": "object",
                "properties": {
                    "habit": {"type": "string", "maxLength": MAX_HABIT_CHARS},
                    "replies": {"type": "integer"},
                },
                "required": ["habit", "replies"],
            },
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
    """The habits named, cleaned and bounded, or None if the answer was malformed. A habit the
    model saw in fewer than MIN_SEEN_IN replies is dropped, so weak or invented ones never count."""
    raw = data.get("habits") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    habits: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        text, seen = item.get("habit"), item.get("replies")
        if not isinstance(text, str) or isinstance(seen, bool) or not isinstance(seen, int):
            return None
        cleaned = " ".join(text.split())[:MAX_HABIT_CHARS]
        if cleaned and seen >= MIN_SEEN_IN:
            habits.append(cleaned)
    return habits[:MAX_HABITS]


def note_for(habits: Sequence[str]) -> str | None:
    if not habits:
        return None
    return get("notes/habit-moves").render(habits="; ".join(habits))
