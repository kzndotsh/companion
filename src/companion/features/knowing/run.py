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
from companion.kit.current import decide
from companion.kit.features import Feature, Offer, Offered, asking
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment

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
KNOWING = Feature("memory map", note=map_offer, after_theirs=label_new)
