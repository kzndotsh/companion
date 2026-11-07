"""Writing what they were talking about for the memories that want it (J51), after each memory pass
and once for the memories already kept."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.extractor import StructuredModel
from companion.core.quoted import AFTER, BEFORE, build_prompt, wants_context
from companion.core.types import RelationshipId
from companion.features.upkeep.context.logic import PROMPT, SCHEMA, parse
from companion.features.upkeep.context.store import BeliefContexts
from companion.kit.ask import Judge, ask
from companion.kit.features import Feature
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.context")
CONTEXT_WRITER = Judge(
    "context",
    PROMPT,
    SCHEMA,
    parse,
    timeout=30.0,  # one memory and the messages around it
    unread="no context for this memory yet",
)


@dataclass(frozen=True, slots=True)
class Written:
    written: int = 0
    cost_usd: float = 0.0


async def write_missing(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime, *, limit: int = 20
) -> Written:
    have = store.belief_contexts(rel)
    todo = [b for b in store.user_beliefs(rel) if wants_context(b) and b.id not in have][:limit]
    if not todo:
        return Written()
    history = store.whole_history(rel)
    where = {u.id: i for i, u in enumerate(history)}
    written, cost = 0, 0.0
    for b in todo:
        i = where.get(b.evidence[0].utterance_id)
        if i is None:
            continue
        around = history[max(0, i - BEFORE) : i + 1 + AFTER]
        got = await ask(extractor, CONTEXT_WRITER, build_prompt(b, around))
        if got is None:
            continue
        cost += got.cost_usd
        context = got.value
        store.part(BeliefContexts).add(rel, b.id, context, prompt=PROMPT.ref, at=now)
        written += 1
    log.debug("memory context: %d written, $%.4f", written, cost)
    return Written(written, cost)


CONTEXT = Feature("context", after_theirs=write_missing)  # what a feeling was about (J51)
