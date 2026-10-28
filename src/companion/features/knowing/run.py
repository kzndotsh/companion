"""Label memories that have no label yet (J48). Runs after the memory pass and from the CLI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.spend import purpose
from companion.core.types import Json, RelationshipId
from companion.features.knowing.logic import (
    LABEL_BATCH,
    LABEL_PROMPT,
    LABEL_SCHEMA,
    MAP_EVERY,
    WOULD_ASK,
    label_prompt,
    parse_labels,
    pick_gap,
)
from companion.loops.current import decide
from companion.loops.features import Feature, Offer, Offered
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.loops.features import Moment

log = logging.getLogger("companion.knowing")


@dataclass(frozen=True, slots=True)
class Labelled:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def label_new(
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
) -> Labelled:
    """Label up to `batches` batches of current memories that have none. A failed call labels
    nothing and is tried again next pass."""
    done = cost = 0
    for _ in range(batches):
        have = store.belief_labels(rel)
        todo = [b for b in store.user_beliefs(rel) if b.id not in have][:LABEL_BATCH]
        if not todo:
            break
        text, refs = label_prompt(todo)
        try:
            with purpose("knowing"):
                result = await extractor.extract(LABEL_PROMPT.text, text, LABEL_SCHEMA)
        except Exception as err:
            log.warning("memory labels failed: %r", err)
            break
        found = parse_labels(result.data, refs)
        cost += result.cost_usd
        if not found:
            break
        store.add_belief_labels(rel, found, result.model, LABEL_PROMPT.ref, now)
        done += len(found)
    have = store.belief_labels(rel)
    left = sum(b.id not in have for b in store.user_beliefs(rel))
    log.debug("memory labels: %d labelled, %d left, $%.4f", done, left, cost)
    return Labelled(done, left, cost)


def map_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """The gap it would ask about on a casual turn, at most once a day (J48, shadow). Nothing
    reaches the talker. The name comes first, so nothing is picked while that note is offered."""
    del found
    c, t = m.c, m.t
    asking_name = bool(so_far["name"].lines)
    if not m.casual or asking_name or c.store.decided_since(c.rel, WOULD_ASK, t.now - MAP_EVERY):
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
    return Offer(after=(lambda: decide(c, t, WOULD_ASK, detail),))


# Each new memory placed in their life, and the gap it would ask about (shadow, logged only).
KNOWING = Feature("memory map", note=map_offer, after_theirs=label_new)
