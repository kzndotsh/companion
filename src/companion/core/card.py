"""The state card: what the companion carries into every turn about the person.

Beliefs are split by sensitivity. Ordinary ones are usable in conversation. Sensitive ones are
held: the companion knows them, so it does not ask again and does not contradict them, but it
does not raise them unprompted. Listening is allowed before saying.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Belief, BeliefKind

HOLD_AT = 2
MAX_ITEMS = 15
KIND_ORDER = {
    kind: i
    for i, kind in enumerate(
        [
            BeliefKind.BOUNDARY,
            BeliefKind.PROMISE,
            BeliefKind.TELL,
            BeliefKind.TRAIT,
            BeliefKind.STATE,
            BeliefKind.THREAD,
            BeliefKind.PREFERENCE,
            BeliefKind.EVENT,
        ]
    )
}


@dataclass(frozen=True, slots=True)
class Card:
    usable: tuple[Belief, ...]
    held: tuple[Belief, ...]

    @property
    def empty(self) -> bool:
        return not self.usable and not self.held


def build_card(beliefs: Sequence[Belief], max_items: int = MAX_ITEMS) -> Card:
    ranked = sorted(beliefs, key=lambda b: (KIND_ORDER[b.kind], -b.valid_from.timestamp()))
    chosen = ranked[:max_items]
    return Card(
        usable=tuple(b for b in chosen if b.sensitivity < HOLD_AT),
        held=tuple(b for b in chosen if b.sensitivity >= HOLD_AT),
    )


def render(card: Card) -> str:
    """Plain text for the volatile part of the user message. Empty when there is nothing."""
    parts: list[str] = []
    if card.usable:
        parts.append(
            "[What you remember about them. Use it naturally, never recite it:\n"
            + "\n".join(f"- {b.claim}" for b in card.usable)
            + "]"
        )
    if card.held:
        parts.append(
            "[Also known, but only touch it if they bring it up:\n"
            + "\n".join(f"- {b.claim}" for b in card.held)
            + "]"
        )
    return "\n".join(parts)
