"""Label memories that have no label yet (J48). Runs after the memory pass and from the CLI."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.types import Belief, Json, RelationshipId
from companion.features.curiosity.map.logic import (
    ASKED,
    LABEL_BATCH,
    LABEL_PROMPT,
    LABEL_SCHEMA,
    MAP_EVERY,
    ask_note,
    label_prompt,
    parse_labels,
    pick_gap,
)
from companion.kit.ask import Judge, ask, whole_answer
from companion.kit.batches import Batch, Swept, label_in_batches
from companion.kit.current import decide
from companion.kit.features import Feature, NoteName, Offer, Offered, asking
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment

log = logging.getLogger("companion.knowing")
# The labels are only good for the refs the prompt numbered, so the caller finishes the reading.
LABELLER = Judge(
    "knowing",
    LABEL_PROMPT,
    LABEL_SCHEMA,
    whole_answer,
    timeout=60.0,  # one batch of memories a call
    unread="nothing labelled; tried again next pass",
)


async def label_new(
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
) -> Swept:
    """Label up to `batches` batches of current memories that have none. A failed call labels
    nothing and is tried again next pass."""

    def todo() -> list[Belief]:
        have = store.belief_labels(rel)
        return [b for b in store.user_beliefs(rel) if b.id not in have][:LABEL_BATCH]

    async def label(memories: Sequence[Belief]) -> Batch:
        text, refs = label_prompt(memories)
        result = await ask(extractor, LABELLER, text)
        if result is None:
            return Batch(stop=True)
        found = parse_labels(result.value, refs)
        if not found:
            return Batch(cost_usd=result.cost_usd, stop=True)
        store.add_belief_labels(rel, found, result.model, LABEL_PROMPT.ref, now)
        return Batch(len(found), result.cost_usd)

    def left() -> int:
        have = store.belief_labels(rel)
        return sum(b.id not in have for b in store.user_beliefs(rel))

    return await label_in_batches(
        "memory labels", batches=batches, todo=todo, label=label, left=left
    )


def map_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """On a casual turn, at most once in three days, a note to ask one light question about the
    thinnest part of the map (J48). Nothing is offered while a note before it asks them something,
    so the name comes first."""
    del found
    c, t = m.c, m.t
    if not m.casual or asking(so_far) or c.store.decided_since(c.rel, ASKED, t.now - MAP_EVERY):
        return Offer()
    gap = pick_gap(c.store.user_beliefs(c.rel), c.store.belief_labels(c.rel))
    if gap is None:
        return Offer()
    detail: dict[str, Json] = {
        "why": gap.reason,
        "domain": gap.domain.value,
        "depth": gap.depth.value,
        "counts": {d.value: n for d, n in gap.counts.items()},
    }
    return Offer((ask_note(gap),), (lambda: decide(c, t, ASKED, detail),), asks=True)


# Each new memory placed in their life, and a light question about the thinnest part.
KNOWING = Feature(NoteName.MEMORY_MAP, note=map_offer, after_theirs=label_new)
