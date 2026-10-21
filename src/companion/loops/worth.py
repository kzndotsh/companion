"""Labelling memories as about their life, about the bot, or routine (`core/worth.py`). New
memories are acted on when the three reads agree; memories kept before become questions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from companion.core.context import AFTER, BEFORE, build_prompt
from companion.core.extractor import Extractor
from companion.core.types import Belief, RelationshipId
from companion.core.worth import PROMPT, ROUTINE_DAYS, SCHEMA, Label, read, to_ask, verdict
from companion.loops.reads import read_times
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.worth")
FAR = datetime(9999, 1, 1, tzinfo=UTC)
WHOLE = 100_000
DROPPED = "a remark about the bot, not their life (three reads agreed)"
EXPIRED = "a routine moment, a week on"


@dataclass(frozen=True, slots=True)
class Labelled:
    labelled: int = 0
    dropped: int = 0
    questions: int = 0
    cost_usd: float = 0.0


async def _reads(extractor: Extractor, prompt: str) -> tuple[tuple[str | None, ...], float]:
    got = await read_times(extractor, PROMPT.text, prompt, SCHEMA, read, spend="worth")
    return got.values, got.cost_usd


async def label(  # noqa: PLR0913
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    now: datetime,
    *,
    act_since: datetime | None,
    limit: int = 20,
) -> Labelled:
    """Label the memories not yet labelled. One recorded since `act_since` (a new memory) is acted
    on: an agreed remark about the bot is retired at once. One kept before becomes a question."""
    from companion.loops.curate import retire  # noqa: PLC0415  curate imports the memory pass

    done = store.checked_memories(rel, prompt="system/memory-worth")
    todo: list[Belief] = [b for b in store.user_beliefs(rel) if b.id not in done][:limit]
    if not todo:
        return Labelled()
    history = store.history_before(rel, FAR, WHOLE)
    where = {u.id: i for i, u in enumerate(history)}
    dropped = questions = 0
    cost = 0.0
    for b in todo:
        i = where.get(b.evidence[0].utterance_id)
        around = history[max(0, i - BEFORE) : i + 1 + AFTER] if i is not None else []
        reads, spent = await _reads(extractor, build_prompt(b, around))
        cost += spent
        found = verdict(reads)
        act = act_since is not None and b.recorded_at >= act_since
        stored = found if act else to_ask(found)
        store.add_memory_check(rel, b.id, None, reads, stored, prompt=PROMPT.ref, at=now)
        if act and found == Label.ABOUT_THE_BOT:
            retire(store, rel, b.id, DROPPED, now)
            dropped += 1
        questions += stored not in (Label.KEEP, Label.ABOUT_THE_BOT, Label.ROUTINE)
    log.debug("memory worth: %d labelled, %d dropped, %d questions", len(todo), dropped, questions)
    return Labelled(len(todo), dropped, questions, cost)


def expire_routine(store: Store, rel: RelationshipId, now: datetime) -> int:
    """Retire routine moments a week after they were last mentioned."""
    from companion.loops.curate import retire  # noqa: PLC0415  curate imports the memory pass

    routine = {
        c.belief_id
        for c in store.unanswered_checks(rel, [Label.ROUTINE.value])
        if c.other_id is None
    }
    support = store.last_support(rel)
    gone = 0
    for b in store.user_beliefs(rel):
        if b.id in routine and now - support.get(b.id, b.valid_from) > ROUTINE_DAYS:
            retire(store, rel, b.id, EXPIRED, now)
            gone += 1
    return gone
