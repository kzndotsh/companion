"""Label the companion's views that have no kind yet (ADR 0020, phase 1). Runs after the memory pass
and from the CLI. A failed call labels nothing and is tried again next pass."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.extractor import Extractor
from companion.core.lore import (
    BATCH,
    GATE,
    PROMPT,
    READS,
    SCHEMA,
    SHOWN,
    agreed,
    lore,
    parse,
    prompt,
)
from companion.core.relevance import Embedder, nearest
from companion.core.spend import purpose
from companion.core.types import Belief, BeliefId, RelationshipId
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.lore")


@dataclass(frozen=True, slots=True)
class KindsRead:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def label_views(  # noqa: PLR0913
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
    again: bool = False,
) -> KindsRead:
    """Label views with no kind yet, READS times each, keeping a taste only where every read
    agrees. `again` labels every current view anew (the newest label wins)."""
    done = 0
    cost = 0.0
    redo = {b.id for b in store.self_beliefs(rel)} if again else set[BeliefId]()
    for _ in range(batches):
        have = store.view_kinds(rel)
        todo = [b for b in store.self_beliefs(rel) if b.id in redo or b.id not in have][:BATCH]
        if not todo:
            break
        redo -= {b.id for b in todo}
        text, refs = prompt(todo)
        try:
            with purpose("lore"):
                results = await asyncio.gather(
                    *(extractor.extract(PROMPT.text, text, SCHEMA) for _ in range(READS))
                )
        except Exception as err:
            log.warning("view kinds failed: %r", err)
            break
        cost += sum(r.cost_usd for r in results)
        found = agreed([parse(r.data, refs) for r in results], refs.values())
        store.add_view_kinds(rel, found, model=results[0].model, prompt=PROMPT.ref, at=now)
        done += len(found)
    have = store.view_kinds(rel)
    left = sum(b.id not in have for b in store.self_beliefs(rel))
    log.debug("view kinds: %d labelled, %d left, $%.4f", done, left, cost)
    return KindsRead(done, left, cost)


LOOK_SECONDS = 2.0  # a slow embedding only means no tastes are shown this turn


@dataclass(frozen=True, slots=True)
class Nearest:
    tastes: tuple[tuple[Belief, float], ...]
    cost_usd: float


async def nearest_tastes(  # noqa: PLR0913, PLR0917
    store: Store,
    embedder: Embedder,
    rel: RelationshipId,
    model: str,
    said: str,
    now: datetime,
) -> Nearest | None:
    """Its tastes nearest their message, at most SHOWN and none below GATE, embedding any taste that
    has no vector yet in the same call. None when the call failed or was slow."""
    tastes = lore(store.self_beliefs(rel), store.view_kinds(rel))
    if not tastes:
        return Nearest((), 0.0)
    have = store.belief_embeddings(rel, model)
    missing = [b for b in tastes if b.id not in have]
    try:
        with purpose("lore"):
            got = await asyncio.wait_for(
                embedder.embed([said, *(b.claim for b in missing)]), LOOK_SECONDS
            )
    except Exception as err:
        log.warning("lore look-up failed or was slow; no tastes shown: %r", err)
        return None
    if missing:
        fresh = dict(zip((b.id for b in missing), got.vectors[1:], strict=True))
        store.add_belief_embeddings(rel, fresh, model, now)
        have = {**have, **fresh}
    near = nearest(got.vectors[0], tastes, have, k=SHOWN)
    return Nearest(tuple((b, s) for b, s in near if s >= GATE), got.cost_usd)
