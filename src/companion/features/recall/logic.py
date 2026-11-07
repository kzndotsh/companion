"""Recall: the memories a reply gets beyond the card, by trigger.

The card holds fifteen memories a turn out of well over a hundred, so most of what it knows never
reaches a reply on its own. Two triggers bring more:

- asked: they ask it to remember, or say it forgot. A small model reads the topic, the last few
  messages and every memory they may be asked about, and points at the ones meant (`core/recall.py`,
  `kit/recall.py`, which the guess shares).
- near: an embedding of their message finds the nearest memories, and a small model picks at most
  three of those, or none (ADR 0018).

Both follow one rule for what may be found (`eligible`) and one for what is shown (`extras`)."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.frames import is_assertable
from companion.core.recall import ASKED_SENSITIVITY, MAX_SENSITIVITY
from companion.core.types import Belief, BeliefId, Json, Sensitivity
from companion.prompts import get

PROMPT = get("system/relevance")
SHADOW = "relevance: what it would have kept in mind (shadow)"
LIVE = "relevance: what it was shown"
GATE = 0.42  # live: the small model picks only when the closest memory is this near (1 turn in 5)
SHOWN = 2  # live: at most this many picks reach the talker, none already on the card
MAX_PICKS = 3

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"labels": {"type": "array", "items": {"type": "string"}}},
    "required": ["labels"],
}


def eligible(
    beliefs: Sequence[Belief],
    *,
    asked: bool,
    sharing: bool,
    hidden: frozenset[BeliefId] = frozenset(),
) -> list[Belief]:
    """What a trigger may find: stated for real, and never a `hidden` memory (the intimate lane,
    which the roleplay card shows instead, ADR 0026). Asked, anything they said up to crisis level,
    since they asked for it. Otherwise never crisis-level, and held (sensitive) memories only when
    they share something, the same rule as the card."""
    top = ASKED_SENSITIVITY if asked else MAX_SENSITIVITY if sharing else Sensitivity.PRIVATE
    return [b for b in beliefs if is_assertable(b) and b.sensitivity <= top and b.id not in hidden]


def extras(
    near: Sequence[tuple[BeliefId, str]],
    *,
    on_card: frozenset[BeliefId],
    recalled: Sequence[BeliefId],
) -> list[str]:
    """The near picks worth a line: none already on the card or already shown by the asked note,
    at most SHOWN. Before, a memory the asked note showed came again in the near note on 5 of 17
    asked turns (2026-11-05)."""
    seen = on_card | frozenset(recalled)
    return [claim for bid, claim in near if bid not in seen][:SHOWN]


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
    "extras",
    "parse",
]
