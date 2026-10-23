"""The overnight memory check (ADR 0019): read each memory a week old or more once, three times;
close a faded passing moment, and leave every other finding as a question for the owner. In shadow
it logs what it would have closed and closes nothing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from companion.core.card import faded
from companion.core.consolidate import (
    CHECK,
    CHECK_SCHEMA,
    PAIR,
    PAIR_SCHEMA,
    check_prompt,
    pair_prompt,
    plan_for,
    read_label,
    read_relation,
    same_as,
    verdict,
)
from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import Belief, Depth, Domain, RelationshipId
from companion.core.vectors import Embedder, nearest
from companion.loops.curate import log_would_close, retire
from companion.loops.embed import embed_missing
from companion.loops.reads import read_times
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.consolidate")
SETTLED_DAYS = 7  # a memory is only read once it has had a week to be restated
PER_NIGHT = 40
CLOSED = "a passing moment, faded from the card (ADR 0019)"


@dataclass(frozen=True, slots=True)
class Night:
    checked: int = 0
    closed: int = 0
    questions: int = 0
    cost_usd: float = 0.0


async def _reads(judge: Extractor, b: Belief, today: str) -> tuple[tuple[str | None, ...], float]:
    got = await read_times(
        judge, CHECK.text, check_prompt(b, today), CHECK_SCHEMA, read_label, spend="consolidate"
    )
    return got.values, got.cost_usd


async def nightly(  # noqa: PLR0913
    store: Store,
    judge: Extractor,
    rel: RelationshipId,
    now: datetime,
    tz: tzinfo,
    *,
    mode: str,
) -> Night:
    checked = store.checked_memories(rel)
    support = store.last_support(rel)
    labels = store.belief_labels(rel)
    everyday = {
        bid for bid, x in labels.items() if x.domain is Domain.DAILY and x.depth is Depth.SURFACE
    }
    due = sorted(
        (
            b
            for b in store.user_beliefs(rel)
            if b.id not in checked
            and now - support.get(b.id, b.valid_from) >= timedelta(days=SETTLED_DAYS)
        ),
        key=lambda b: support.get(b.id, b.valid_from),
    )[:PER_NIGHT]
    today = now.astimezone(tz).date().isoformat()
    closed = questions = 0
    cost = 0.0
    for b in due:
        reads, spent = await _reads(judge, b, today)
        cost += spent
        found = verdict(reads)
        store.add_memory_check(rel, b.id, None, reads, found, prompt=CHECK.ref, at=now)
        last = support.get(b.id, b.valid_from)
        plan = plan_for(b, found, faded=b.id in everyday and faded(b, last, now))
        if plan.close:
            closed += 1
            if mode == "on":
                retire(store, rel, b.id, CLOSED, now)
            else:
                log_would_close(store, b, CLOSED, now)
        questions += plan.ask
    log.info(
        "memory check: %d read, %d %s, %d questions for the owner, $%.4f",
        len(due),
        closed,
        "closed" if mode == "on" else "would be closed (shadow)",
        questions,
        cost,
    )
    return Night(len(due), closed, questions, cost)


GATE = 0.55  # below this the nearest memory is not worth asking about (at 0.6, 25 of 31 caught)


@dataclass(frozen=True, slots=True)
class SameCheck:
    """At write time: is a new memory the same as an existing one? Three pair reads on the nearest
    memory by embedding; in shadow it only logs, `on` stores the new one as evidence instead."""

    judge: Extractor
    embedder: Embedder
    model: str
    mode: str

    async def find(
        self, store: Store, rel: RelationshipId, new: Belief, now: datetime
    ) -> Belief | None:
        try:
            return await self._find(store, rel, new, now)
        except Exception as err:  # the memory is stored as usual
            log.warning("same check failed: %r", err)
            return None

    async def _find(
        self, store: Store, rel: RelationshipId, new: Belief, now: datetime
    ) -> Belief | None:
        await embed_missing(store, self.embedder, rel, self.model, now)
        pool = [b for b in store.user_beliefs(rel) if b.id != new.id]
        with purpose("consolidate"):
            query = await self.embedder.embed([new.claim])
        near = nearest(query.vectors[0], pool, store.belief_embeddings(rel, self.model), k=1)
        if not near or near[0][1] < GATE:
            return None
        older = near[0][0]

        got = await read_times(
            self.judge,
            PAIR.text,
            pair_prompt(older, new),
            PAIR_SCHEMA,
            read_relation,
            spend="consolidate",
        )
        if got.failed:  # the memory is stored as usual; nothing is recorded about the pair
            return None
        reads = got.values
        found = verdict(reads)
        store.add_memory_check(rel, older.id, new.id, reads, found, prompt=PAIR.ref, at=now)
        return older if same_as(found) else None
