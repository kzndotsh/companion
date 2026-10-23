"""The made-up facts rate (G42, J9): how often a reply states something about the user that neither
the conversation nor its memory supports. A cheap judge lists each statement about the user's life
with what supports it; code keeps only statements quoted from the reply and said to them. On real
replies the cheap judge's flags were right only about one time in twelve, so they are candidates:
the rate is what a stronger reader confirms (`companion invented --dump`, read by a Claude judge in
a review). Measured on demand, never on the reply path.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from companion.core.types import Json
from companion.prompts import get

PROMPT = get("system/invented-judge")
SYSTEM = PROMPT.text
_TO_THEM = re.compile(r"\b(you|your|yours|you're|youre|you've|you'd|u|ur)\b", re.IGNORECASE)


class Support(StrEnum):
    CONVERSATION = "conversation"
    MEMORY = "memory"
    NONE = "none"


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "support": {"type": "string", "enum": [s.value for s in Support]},
                },
                "required": ["quote", "support"],
            },
        }
    },
    "required": ["statements"],
}


@dataclass(frozen=True, slots=True)
class Statement:
    quote: str
    support: Support


def build_prompt(recent: Sequence[tuple[str, str]], memories: Sequence[str], reply: str) -> str:
    talk = [f"[{'USER' if who == 'user' else 'COMPANION'}] {text}" for who, text in recent]
    known = [f"- {m}" for m in memories] or ["(nothing)"]
    return "\n".join(
        [
            "Recent messages:",
            *talk,
            "",
            "Its memory of the user:",
            *known,
            "",
            f"The reply: {reply}",
        ]
    )


def parse(data: Json, reply: str) -> list[Statement] | None:
    """The statements quoted from the reply that address them, with known support. None for an
    answer of the wrong shape; a quote not in the reply, or not said to them, is dropped."""
    items = data.get("statements") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    low = reply.lower()
    out: list[Statement] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        quote, support = item.get("quote"), item.get("support")
        found = isinstance(quote, str) and quote.strip() and quote.strip().lower() in low
        if found and _TO_THEM.search(str(quote)) and support in set(Support):
            out.append(Statement(str(quote).strip(), Support(str(support))))
    return out


def invented(statements: Sequence[Statement]) -> list[Statement]:
    return [s for s in statements if s.support is Support.NONE]


def report(checks: Sequence[tuple[str, Sequence[Statement]]], days: int) -> str:
    """The rate first: replies with at least one unsupported statement about them, then examples."""
    made = [(reply, invented(s)) for reply, s in checks]
    bad = [(reply, s) for reply, s in made if s]
    about = sum(1 for _, s in checks if s)
    head = (
        f"last {days} days: {len(checks)} replies checked, {about} said something about them,"
        f" {len(bad)} candidates for something nothing supports (unconfirmed: the cheap judge is"
        " right about one time in twelve; confirm them with --dump and a stronger reader)"
    )
    lines = [head]
    lines += [f"  - {s[0].quote!r}  in  {reply[:90]!r}" for reply, s in bad[-8:]]
    return "\n".join(lines) + "\n"
