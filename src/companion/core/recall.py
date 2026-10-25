"""Looking something up when they ask the companion to remember.

The card shows about fifteen beliefs a turn, ranked, out of hundreds. When they ask "you know this
one" about something that did not make the card, the reply had nothing to go on and improvised (the
owner's flag of 2026-10-18: three burger beliefs in memory, none on the card, so it guessed tacos
and joked about the one music belief it could see). On those turns only, a small model reads the
topic and every candidate belief and points at the ones that bear on it; code keeps only labels it
showed and never a crisis-level belief, and the picks ride the system block for that turn.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from companion.core.frames import is_assertable
from companion.core.types import Belief, Json
from companion.prompts import get

PROMPT = get("system/recall")
SYSTEM = PROMPT.text
_NOTE = get("notes/recall")
_EMPTY = get("notes/recall-empty")
MAX_PICKS = 5
MAX_SENSITIVITY = 2  # never look up crisis-level beliefs on its own

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"labels": {"type": "array", "items": {"type": "string"}}},
    "required": ["labels"],
}


def candidates(beliefs: Sequence[Belief]) -> dict[str, Belief]:
    """Short labels (r1, r2, ...) for the beliefs it may look up: stated for real and not crisis."""
    usable = [b for b in beliefs if is_assertable(b) and b.sensitivity <= MAX_SENSITIVITY]
    return {f"r{i}": b for i, b in enumerate(usable, start=1)}


def build_prompt(
    topic: str,
    labelled: Mapping[str, Belief],
    when: Mapping[str, str] | None = None,
    today: str = "",
) -> str:
    """The question and the numbered list. With `when` (label to "today", "3 days ago") and `today`,
    each line says when it was last said, so "what I had earlier" can find today's meal: without
    them the judge picked older food preferences instead (owner's flag 2026-10-25)."""
    lines = [
        f"[{label}] {b.claim}" + (f" (said {when[label]})" if when and label in when else "")
        for label, b in labelled.items()
    ]
    head = [f"Today is {today}."] if today else []
    return "\n".join([*head, f"They asked you to remember: {topic}", "", "What you know:", *lines])


def parse(data: Json, labelled: Mapping[str, Belief]) -> list[Belief]:
    """The beliefs picked, in order, only from labels that were shown, at most five."""
    raw = data.get("labels") if isinstance(data, dict) else None
    picked: list[Belief] = []
    for label in raw if isinstance(raw, list) else []:
        b = labelled.get(str(label).strip().strip("[]").strip())  # the list shows "[r12]"
        if b is not None and b not in picked:
            picked.append(b)
    return picked[:MAX_PICKS]


def recall_note(picked: Sequence[Belief]) -> str:
    """The block for the system block. When nothing was found it says so, so the reply owns the
    gap instead of guessing (J30)."""
    if not picked:
        return _EMPTY.text
    return _NOTE.render(items="\n".join(f"- {b.claim}" for b in picked))
