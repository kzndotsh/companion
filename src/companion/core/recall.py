"""Looking something up when they ask the companion to remember.

The card shows about fifteen beliefs a turn, ranked, out of hundreds. When they ask "you know this
one" about something that did not make the card, the reply had nothing to go on and improvised (the
owner's flag of 2026-10-18: three burger beliefs in memory, none on the card, so it guessed tacos
and joked about the one music belief it could see). On those turns only, a small model reads the
topic and every candidate belief and points at the ones that bear on it; code keeps only labels it
showed, and the picks ride the system block for that turn.

When they ask, the look-up also reads the last few messages of the conversation, both sides, since
the topic is the listening judge's guess, and may reach their most sensitive memories, since they
asked for them. On 2026-10-29 "the serious stuff we talked about early" was guessed as self-harm and
found mood memories in 12 of 12 reads; with the conversation and the most sensitive memories it
found the one they meant in 34 of 34. Their side alone was not enough: "you know this already" only
means something next to the question it answers. A look-up made on its own, with no question from
them, still stops below crisis level.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from companion.core.frames import is_assertable
from companion.core.types import Belief, BeliefId, Json, Sensitivity
from companion.prompts import get

PROMPT = get("system/recall")
SYSTEM = PROMPT.text
MAX_PICKS = 5
# What a look-up may find. Unprompted, up to a guarded memory and never a crisis-level one; the
# near and asked look-ups share these two limits.
MAX_SENSITIVITY = Sensitivity.DELICATE
# When they ask it to remember, anything they said may be found.
ASKED_SENSITIVITY = Sensitivity.GRAVE

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"labels": {"type": "array", "items": {"type": "string"}}},
    "required": ["labels"],
}


def usable(
    beliefs: Sequence[Belief],
    max_sensitivity: Sensitivity,
    hidden: frozenset[BeliefId] = frozenset(),
) -> list[Belief]:
    """What either trigger may find: stated for real, up to `max_sensitivity`, and never a `hidden`
    memory."""
    return [
        b
        for b in beliefs
        if is_assertable(b) and b.sensitivity <= max_sensitivity and b.id not in hidden
    ]


def candidates(
    beliefs: Sequence[Belief], max_sensitivity: Sensitivity = MAX_SENSITIVITY
) -> dict[str, Belief]:
    """Short labels (r1, r2, ...) for the beliefs it may look up: stated for real and, unless they
    asked, not crisis."""
    return {f"r{i}": b for i, b in enumerate(usable(beliefs, max_sensitivity), start=1)}


def build_prompt(
    topic: str,
    labelled: Mapping[str, Belief],
    when: Mapping[str, str] | None = None,
    today: str = "",
    recent: Sequence[str] = (),
) -> str:
    """The question and the numbered list. With `when` (label to "today", "3 days ago") and `today`,
    each line says when it was last said, so "what I had earlier" can find today's meal: without
    them the judge picked older food preferences instead (owner's flag 2026-10-25). With `recent`
    (the last messages, oldest first, each starting "they:" or "you:") the judge works out from them
    what a vague ask means."""
    lines = [
        f"[{label}] {b.claim}" + (f" (said {when[label]})" if when and label in when else "")
        for label, b in labelled.items()
    ]
    head = [f"Today is {today}."] if today else []
    said = ["", "The last messages:", *(f"- {m}" for m in recent)] if recent else []
    return "\n".join(
        [*head, f"They asked you to remember: {topic}", *said, "", "What you know:", *lines]
    )


def picked(data: Json, labelled: Mapping[str, Belief], limit: int) -> list[Belief]:
    """The beliefs a judge picked, in order, only from labels that were shown, at most `limit`."""
    raw = data.get("labels") if isinstance(data, dict) else None
    chosen: list[Belief] = []
    for label in raw if isinstance(raw, list) else []:
        b = labelled.get(str(label).strip().strip("[]").strip())  # the list shows "[r12]"
        if b is not None and b not in chosen:
            chosen.append(b)
    return chosen[:limit]


def parse(data: Json, labelled: Mapping[str, Belief]) -> list[Belief]:
    """The beliefs picked, in order, only from labels that were shown, at most five."""
    return picked(data, labelled, MAX_PICKS)
