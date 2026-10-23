"""Label memories that have no label yet (J48). Runs after the memory pass and from the CLI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.features.knowing.logic import (
    LABEL_BATCH,
    LABEL_PROMPT,
    LABEL_SCHEMA,
    label_prompt,
    parse_labels,
)
from companion.loops.features import Feature
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.knowing")


@dataclass(frozen=True, slots=True)
class Labelled:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def label_new(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime, *, batches: int = 1
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


KNOWING = Feature("memory map", after_theirs=label_new)  # each new memory placed in their life
