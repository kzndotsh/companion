"""Which of the companion's own views, if any, does a flagged reply implicate?

The user flagged a turn and left a short note. Closing every view that turn carried is too blunt: a
flag about a game that lost its thread closed four unrelated views. A model reads the note, the
exchange and the views, and names only those the reply relied on or contradicted. Unclear means
none, because closing a view that was fine costs more than keeping one that was not.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from companion.core.types import Belief, Json, unit_interval
from companion.prompts import get

MIN_CONFIDENCE = 0.7

PROMPT = get("system/views-implicated")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "implicated": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": ["implicated", "confidence"],
}


@dataclass(frozen=True, slots=True)
class Implication:
    labels: frozenset[str]
    confidence: float


def build_prompt(user: str, reply: str, note: str, views: Mapping[str, Belief]) -> str:
    return "\n".join(
        [
            f"User's message: {user}",
            f"Companion's reply: {reply}",
            f"The user's note on the flag: {note or '(none)'}",
            "",
            "Views the companion holds:",
            *[f"[{k}] {b.claim}" for k, b in views.items()],
        ]
    )


def parse(data: Json, valid: set[str]) -> Implication | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Json]", data)
    raw, conf = d.get("implicated"), d.get("confidence")
    confidence = unit_interval(conf)
    if not isinstance(raw, list) or confidence is None:
        return None
    labels = frozenset(x for x in cast("list[Json]", raw) if isinstance(x, str) and x in valid)
    return Implication(labels, confidence)
