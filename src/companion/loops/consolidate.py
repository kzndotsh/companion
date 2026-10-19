"""The overnight memory check (ADR 0019): read each memory a week old or more once, three times;
close a faded passing moment, and leave every other finding as a question for the owner. In shadow
it logs what it would have closed and closes nothing."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from companion.core.card import faded
from companion.core.consolidate import (
    CHECK,
    CHECK_SCHEMA,
    READS,
    check_prompt,
    plan_for,
    read_label,
    verdict,
)
from companion.core.extractor import Extractor
from companion.core.knowing import Depth, Domain
from companion.core.spend import purpose
from companion.core.types import Belief, RelationshipId
from companion.loops.curate import log_would_close, retire
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
    async def one() -> tuple[str | None, float]:
        try:
            with purpose("consolidate"):
                got = await judge.extract(CHECK.text, check_prompt(b, today), CHECK_SCHEMA)
        except Exception as err:  # a failed read is never agreement, so nothing is acted on
            log.warning("memory check failed: %r", err)
            return None, 0.0
        return read_label(got.data), got.cost_usd

    results = await asyncio.gather(*(one() for _ in range(READS)))
    return tuple(r for r, _ in results), sum(c for _, c in results)


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
