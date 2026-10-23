"""Writing what they were talking about for the memories that want it (J51), after each memory pass
and once for the memories already kept."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from companion.core.context import PROMPT, SCHEMA, parse, wants_context
from companion.core.extractor import Extractor
from companion.core.quoted import AFTER, BEFORE, build_prompt
from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.loops.features import Feature
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.context")
FAR = datetime(9999, 1, 1, tzinfo=UTC)
WHOLE = 100_000


@dataclass(frozen=True, slots=True)
class Written:
    written: int = 0
    cost_usd: float = 0.0


async def write_missing(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime, *, limit: int = 20
) -> Written:
    have = store.belief_contexts(rel)
    todo = [b for b in store.user_beliefs(rel) if wants_context(b) and b.id not in have][:limit]
    if not todo:
        return Written()
    history = store.history_before(rel, FAR, WHOLE)
    where = {u.id: i for i, u in enumerate(history)}
    written, cost = 0, 0.0
    for b in todo:
        i = where.get(b.evidence[0].utterance_id)
        if i is None:
            continue
        around = history[max(0, i - BEFORE) : i + 1 + AFTER]
        try:
            with purpose("context"):
                got = await extractor.extract(PROMPT.text, build_prompt(b, around), SCHEMA)
        except Exception as err:
            log.warning("memory context failed: %r", err)
            continue
        cost += got.cost_usd
        context = parse(got.data)
        if context is None:
            continue
        store.add_belief_context(rel, b.id, context, prompt=PROMPT.ref, at=now)
        written += 1
    log.debug("memory context: %d written, $%.4f", written, cost)
    return Written(written, cost)


CONTEXT = Feature("context", after_theirs=write_missing)  # what a feeling was about (J51)
