"""The state card: what the companion carries into every turn about the person.

Beliefs are split two ways. By sensitivity: ordinary ones are usable in conversation, sensitive ones
are held, so the companion knows them and does not ask again but does not raise them unprompted.
By freshness (see `freshness.py`): aging ones are marked as possibly changed, and stale ones leave
the main card. A few stale ordinary ones go in a separate "may be out of date" block so the
companion can check naturally. Stale sensitive ones are left out entirely.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo

from companion.core.freshness import Freshness, status, when_phrase
from companion.core.types import Belief, BeliefId, BeliefKind

HOLD_AT = 2
MAX_ITEMS = 15
MAX_OLDER = 3
# A one-day moment of daily life (a spill, a meal, a long shower: an event the memory map labels
# daily life at surface depth) stops being shown a week after it was last mentioned. It stays in
# memory and the look-ups still find it; it just stops taking one of the card's places. Other
# events, such as starting a project or getting a job, are history and stay.
EVENT_SHOWN_DAYS = 7
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
    views: tuple[Belief, ...] = ()
    crowded: tuple[Belief, ...] = ()  # current, but past the card's size
    kept_back: tuple[Belief, ...] = ()  # sensitive, left out on a casual turn

    @property
    def empty(self) -> bool:
        return not (self.usable or self.held or self.older or self.views)


def build_card(  # noqa: PLR0913
    beliefs: Sequence[Belief],
    support: Mapping[BeliefId, datetime],
    now: datetime,
    max_items: int = MAX_ITEMS,
    views: Sequence[Belief] = (),
    *,
    show_held: bool = True,
    everyday: Collection[BeliefId] = (),
) -> Card:
    """`support` is each belief's freshest evidence time, falling back to valid_from.

    With `show_held` off (a casual turn) sensitive beliefs are left out entirely and their places go
    to ordinary ones: in view, a model links them to unrelated banter and raises them unasked."""
    aged = {
        b.id: Aged(
            (last := support.get(b.id, b.valid_from)),
            status(b.kind, last, now),
        )
        for b in beliefs
    }
    faded = [b for b in beliefs if b.id in everyday and _faded(b, aged[b.id].last_supported, now)]
    current = [b for b in beliefs if aged[b.id].status is not Freshness.STALE and b not in faded]
    kept_back = [] if show_held else [b for b in current if b.sensitivity >= HOLD_AT]
    current = [b for b in current if b not in kept_back]
    stale = sorted(
        (b for b in beliefs if aged[b.id].status is Freshness.STALE),
        key=lambda b: -aged[b.id].last_supported.timestamp(),
    )
    ordered = sorted(
        current, key=lambda b: (KIND_ORDER[b.kind], -aged[b.id].last_supported.timestamp())
    )
    ranked, crowded = ordered[:max_items], ordered[max_items:]
    older_pool = [b for b in stale if b.sensitivity < HOLD_AT]
    older = tuple(older_pool[:MAX_OLDER])
    return Card(
        usable=tuple(b for b in ranked if b.sensitivity < HOLD_AT),
        held=tuple(b for b in ranked if b.sensitivity >= HOLD_AT),
        older=older,
        dropped=tuple(b for b in [*stale, *faded] if b not in older),
        aged=aged,
        now=now,
        views=tuple(views),
        crowded=tuple(crowded),
        kept_back=tuple(kept_back),
    )


def _faded(b: Belief, last: datetime, now: datetime) -> bool:
    return (
        b.kind is BeliefKind.EVENT
        and b.sensitivity == 0
        and now - last > timedelta(days=EVENT_SHOWN_DAYS)
    )


def _line(b: Belief, card: Card) -> str:
    a = card.aged[b.id]
    when = when_phrase(a.last_supported, card.now)
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
    if card.views:
        parts.append(
            "[Views of your own that you have expressed and they have approved. Hold to them "
            "unless they give you a real reason to change your mind. If you do change your mind, "
            "say so plainly:\n" + "\n".join(f"- {b.claim}" for b in card.views) + "]"
        )
    return "\n".join(parts)
