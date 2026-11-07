"""Playing along when they invite a guess (J16, owner flag 2026-10-19).

"You know what time it is?" was answered with the clock; they meant coffee time, their most repeated
ritual. Guessing unasked is the risk (their flags on wrong assumptions), so this acts only when they
invite a guess: a small judge says so on a short question, the recall look-up picks what they may
mean from memory, never anything sensitive, and one note asks for a single playful guess as a
question. Each one is logged with what was offered, so guesses can later be scored by kind.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.sensitivity import GUARDED_AT
from companion.core.turn.context import conversation_prompt
from companion.core.types import Belief, Json, Utterance
from companion.prompts import get

JUDGE = get("system/guess-invite")
NOTE = get("notes/guess")
SHORT_QUESTION_WORDS = 10
CONTEXT = 6
MAX_OFFERED = 3
INVITED = "guess: they invited a guess"
SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"invited": {"type": "boolean"}, "about": {"type": "string"}},
    "required": ["invited", "about"],
}


def likely(said: str) -> bool:
    """Whether to ask the judge at all: a short question. Most turns are not, and make no call."""
    return "?" in said and len(said.split()) <= SHORT_QUESTION_WORDS


def judge_prompt(prior: Sequence[Utterance], said: str) -> str:
    return conversation_prompt(prior, said, last=CONTEXT)


@dataclass(frozen=True, slots=True)
class Invitation:
    """The judge's answer: what they invite a guess about, or None when they invite none."""

    about: str | None


def parse(data: Json) -> Invitation | None:
    """The judge's answer, or None when it cannot be read. A no is an answer, not a failure."""
    if not isinstance(data, dict) or not isinstance(invited := data.get("invited"), bool):
        return None
    if not invited:
        return Invitation(None)
    about = data.get("about")
    return (
        Invitation(" ".join(about.split())[:80])
        if isinstance(about, str) and about.strip()
        else None
    )


def offerable(beliefs: Sequence[Belief]) -> list[Belief]:
    return [b for b in beliefs if b.sensitivity < GUARDED_AT]


def note(about: str, offered: Sequence[Belief]) -> str | None:
    if not offered:
        return None
    items = "\n".join(f"- {b.claim}" for b in offered[:MAX_OFFERED])
    return NOTE.render(about=about, items=items)
