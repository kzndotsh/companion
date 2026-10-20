"""Playing along when they invite a guess (J16, owner flag 2026-10-19).

"You know what time it is?" was answered with the clock; they meant coffee time, their most repeated
ritual. Guessing unasked is the risk (their flags on wrong assumptions), so this acts only when they
invite a guess: a small judge says so on a short question, the recall look-up picks what they may
mean from memory, never anything sensitive, and one note asks for a single playful guess as a
question. Each one is logged with what was offered, so guesses can later be scored by kind.
"""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.types import Belief, Json, Speaker, Utterance
from companion.prompts import get

JUDGE = get("system/guess-invite")
NOTE = get("notes/guess")
SHORT_WORDS = 10
CONTEXT = 6
MAX_OFFERED = 3
HELD = 2  # a guess never draws on anything sensitive
INVITED = "guess: they invited a guess"
SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"invited": {"type": "boolean"}, "about": {"type": "string"}},
    "required": ["invited", "about"],
}


def likely(said: str) -> bool:
    """Whether to ask the judge at all: a short question. Most turns are not, and make no call."""
    return "?" in said and len(said.split()) <= SHORT_WORDS


def judge_prompt(prior: Sequence[Utterance], said: str) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in prior[-CONTEXT:]
    ]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {said}"])


def parse(data: Json) -> str | None:
    """What they invite a guess about, or None."""
    if not isinstance(data, dict) or data.get("invited") is not True:
        return None
    about = data.get("about")
    return " ".join(about.split())[:80] if isinstance(about, str) and about.strip() else None


def offerable(beliefs: Sequence[Belief]) -> list[Belief]:
    return [b for b in beliefs if b.sensitivity < HELD]


def note(about: str, offered: Sequence[Belief]) -> str | None:
    if not offered:
        return None
    items = "\n".join(f"- {b.claim}" for b in offered[:MAX_OFFERED])
    return NOTE.render(about=about, items=items)
