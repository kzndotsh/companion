"""What they were talking about when a memory was said (J51).

A memory is written to stand alone, which strips the moment it came from: "is struggling with" a
thing, with no sign of what was being talked about. The owner compared 19 memories alone, with their
own words, and with a short note on the moment: the note won for feelings and sensitive memories (5
of the 6 such picks), the bare memory for tastes, events and projects, and their words almost never.
So a note is written for those memories only and shown beside them on the card.
"""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.types import Belief, BeliefKind, Json, Speaker, Utterance
from companion.prompts import get

PROMPT = get("system/memory-context")
BEFORE, AFTER = 6, 1  # messages around the quote that the note is written from
MAX_WORDS = 25
SENSITIVE = 2

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"context": {"type": "string"}},
    "required": ["context"],
}


def wants_context(b: Belief) -> bool:
    """A feeling or state, or a sensitive memory: where the moment carries the meaning."""
    return b.kind is BeliefKind.STATE or b.sensitivity >= SENSITIVE


def build_prompt(b: Belief, around: Sequence[Utterance]) -> str:
    lines = [f"{'USER' if u.speaker is Speaker.USER else 'COMPANION'}: {u.text}" for u in around]
    return "\n".join(
        [f"Memory: {b.claim}", f'Their words: "{b.evidence[0].quote}"', "", "Conversation:", *lines]
    )


def parse(data: Json) -> str | None:
    """The note as a lower-case clause without a full stop, or None when empty or too long."""
    raw = data.get("context") if isinstance(data, dict) else None
    if not isinstance(raw, str):
        return None
    text = " ".join(raw.split()).rstrip(".")
    if not text or len(text.split()) > MAX_WORDS:
        return None
    return text[0].lower() + text[1:]
