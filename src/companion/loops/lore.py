"""Label the companion's views that have no kind yet (ADR 0020, phase 1). Runs after the memory pass
and from the CLI. A failed call labels nothing and is tried again next pass."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.extractor import Extractor
from companion.core.lore import BATCH, PROMPT, SCHEMA, parse, prompt
from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.lore")


@dataclass(frozen=True, slots=True)
class KindsRead:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def label_views(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime, *, batches: int = 1
) -> KindsRead:
    done = 0
    cost = 0.0
    for _ in range(batches):
        have = store.view_kinds(rel)
        todo = [b for b in store.self_beliefs(rel) if b.id not in have][:BATCH]
        if not todo:
            break
        text, refs = prompt(todo)
        try:
            with purpose("lore"):
                result = await extractor.extract(PROMPT.text, text, SCHEMA)
        except Exception as err:
            log.warning("view kinds failed: %r", err)
            break
        cost += result.cost_usd
        found = parse(result.data, refs)
        if not found:
            break
        store.add_view_kinds(rel, found, model=result.model, prompt=PROMPT.ref, at=now)
        done += len(found)
    have = store.view_kinds(rel)
    left = sum(b.id not in have for b in store.self_beliefs(rel))
    log.debug("view kinds: %d labelled, %d left, $%.4f", done, left, cost)
    return KindsRead(done, left, cost)
