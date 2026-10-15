"""The state card: what the companion carries into every turn about the person.

Beliefs are split two ways. By sensitivity: ordinary ones are usable in conversation, sensitive ones
are held, so the companion knows them and does not ask again but does not raise them unprompted.
By freshness (see `freshness.py`): aging ones are marked as possibly changed, and stale ones leave
the main card. A few stale ordinary ones go in a separate "may be out of date" block so the
companion can check naturally. Stale sensitive ones are left out entirely.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo

from companion.core.freshness import Freshness, age_phrase, status
from companion.core.types import Belief, BeliefId, BeliefKind

HOLD_AT = 2
MAX_ITEMS = 15
MAX_OLDER = 3
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
class Aged:
    last_supported: datetime
    status: Freshness


@dataclass(frozen=True, slots=True)
class Card:
    usable: tuple[Belief, ...]
    held: tuple[Belief, ...]
    older: tuple[Belief, ...]
    dropped: tuple[Belief, ...]
    aged: Mapping[BeliefId, Aged]
    now: datetime

    @property
    def empty(self) -> bool:
        return not (self.usable or self.held or self.older)


def build_card(
    beliefs: Sequence[Belief],
    support: Mapping[BeliefId, datetime],
    now: datetime,
    max_items: int = MAX_ITEMS,
    max_older: int = MAX_OLDER,
) -> Card:
    """`support` is each belief's freshest evidence time, falling back to valid_from."""
    aged = {
        b.id: Aged(
            (last := support.get(b.id, b.valid_from)),
            status(b.kind, last, now),
        )
        for b in beliefs
    }
    current = [b for b in beliefs if aged[b.id].status is not Freshness.STALE]
    stale = sorted(
        (b for b in beliefs if aged[b.id].status is Freshness.STALE),
        key=lambda b: -aged[b.id].last_supported.timestamp(),
    )
    ranked = sorted(
        current, key=lambda b: (KIND_ORDER[b.kind], -aged[b.id].last_supported.timestamp())
    )[:max_items]
    older_pool = [b for b in stale if b.sensitivity < HOLD_AT]
    older = tuple(older_pool[:max_older])
    return Card(
        usable=tuple(b for b in ranked if b.sensitivity < HOLD_AT),
        held=tuple(b for b in ranked if b.sensitivity >= HOLD_AT),
        older=older,
        dropped=tuple(b for b in stale if b not in older),
        aged=aged,
        now=now,
    )


def _line(b: Belief, card: Card) -> str:
    a = card.aged[b.id]
    when = age_phrase(card.now - a.last_supported)
    note = "; may have changed" if a.status is Freshness.AGING else ""
    return f"- {b.claim} (mentioned {when}{note})"


def render(card: Card, tz: tzinfo = UTC) -> str:
    """Plain text for the volatile part of the user message. Empty when there is nothing.

    `tz` is kept so callers need not change; ages are relative, so no zone is needed to print them.
    """
    del tz
    parts: list[str] = []
    if card.usable:
        parts.append(
            "[What you remember about them. Use it naturally, never recite it:\n"
            + "\n".join(_line(b, card) for b in card.usable)
            + "]"
        )
    if card.held:
        parts.append(
            "[Also known, but only touch it if they bring it up:\n"
            + "\n".join(_line(b, card) for b in card.held)
            + "]"
        )
    if card.older:
        parts.append(
            "[Older, and may be out of date. Do not assume these still hold. If it comes up, "
            "check lightly:\n" + "\n".join(_line(b, card) for b in card.older) + "]"
        )
    return "\n".join(parts)
