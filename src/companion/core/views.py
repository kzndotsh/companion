"""Which of the companion's own views reach the card.

A view is something the companion said, so it is a claim about itself made by the thing it
describes. Left alone that is a self-confirming mirror: whatever the model does by default, it
would record, restate and then be held to. Two guards. A view is *settled* once it has been
expressed on two different days, which filters one-off answers given to please someone. A view
reaches the card only when the *user has approved it*, which is what filters a consistent default
the user does not want. Settled is shown to help the user decide. Approval is what counts.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import datetime

from companion.core.types import Belief, BeliefId, BeliefKind, Subject

SETTLED_DAYS = 2
MAX_VIEWS = 8


def is_settled(belief: Belief, days: Mapping[BeliefId, int]) -> bool:
    return (
        belief.subject is Subject.SELF
        and belief.kind is not BeliefKind.EVENT
        and days.get(belief.id, 1) >= SETTLED_DAYS
    )


def card_views(
    beliefs: Sequence[Belief],
    approved: Collection[BeliefId],
    support: Mapping[BeliefId, datetime],
    limit: int = MAX_VIEWS,
) -> tuple[Belief, ...]:
    """The approved views, most recently restated first. Nothing unapproved gets through."""
    chosen = [b for b in beliefs if b.subject is Subject.SELF and b.id in approved]
    chosen.sort(key=lambda b: support.get(b.id, b.valid_from), reverse=True)
    return tuple(chosen[:limit])
