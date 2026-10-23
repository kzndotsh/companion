"""Finding memories about one thing and proposing each group as one (ADR 0019). Proposals only:
the owner answers them in `companion memory review`."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import Belief, RelationshipId
from companion.features.merging.logic import (
    GROUP,
    GROUP_SCHEMA,
    PICK,
    WRITE,
    WRITE_SCHEMA,
    Group,
    agreed,
    listing,
    read_claim,
    read_groups,
)
from companion.loops.reads import read_times
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.merging")
RECENT_DAYS = 2  # the nightly run groups what was recorded in the last two days


@dataclass(frozen=True, slots=True)
class Proposed:
    groups: int = 0
    cost_usd: float = 0.0


async def _group_reads(judge: Extractor, beliefs: Sequence[Belief]) -> tuple[list[Group], float]:
    got = await read_times(
        judge,
        GROUP.text,
        listing(beliefs),
        GROUP_SCHEMA,
        lambda data: read_groups(data, len(beliefs)),
        spend="consolidate",
    )
    return agreed(got.values), got.cost_usd


async def _wording(judge: Extractor, members: Sequence[Belief]) -> tuple[str | None, float]:
    try:
        with purpose("consolidate"):
            got = await judge.extract(WRITE.text, listing(members), WRITE_SCHEMA)
    except Exception as err:
        log.warning("merged wording failed: %r", err)
        return None, 0.0
    return read_claim(got.data), got.cost_usd


async def repick(store: Store, judge: Extractor, rel: RelationshipId, now: datetime) -> Proposed:
    """Propose again, alone, the members the owner said belong together."""
    current = {b.id: b for b in store.user_beliefs(rel)}
    proposals = store.merge_proposals(rel)
    asked = {frozenset(p.members) for p in proposals}
    made, cost = 0, 0.0
    for p in proposals:
        if p.answer is None or not p.answer.startswith(PICK):
            continue
        ids = [p.members[int(n) - 1] for n in p.answer.removeprefix(PICK).split()]
        if frozenset(ids) in asked or not all(i in current for i in ids):
            continue
        members = [current[i] for i in ids]
        claim, spent = await _wording(judge, members)
        cost += spent
        if claim is not None:
            store.add_merge_proposal(rel, ids, claim, prompt=WRITE.ref, at=now)
            asked.add(frozenset(ids))
            made += 1
    return Proposed(made, cost)


async def propose(
    store: Store, judge: Extractor, rel: RelationshipId, beliefs: Sequence[Belief], now: datetime
) -> Proposed:
    """Group these memories and store a proposal for each new group with its merged wording."""
    if len(beliefs) < 2:
        return Proposed()
    groups, cost = await _group_reads(judge, beliefs)
    asked = {frozenset(p.members) for p in store.merge_proposals(rel)}
    made = 0
    for g in groups:
        members = [beliefs[i] for i in sorted(g)]
        ids = frozenset(b.id for b in members)
        if ids in asked:
            continue
        claim, spent = await _wording(judge, members)
        cost += spent
        if claim is None:
            continue
        store.add_merge_proposal(rel, [b.id for b in members], claim, prompt=GROUP.ref, at=now)
        asked.add(ids)
        made += 1
    return Proposed(made, cost)


def _by_day(beliefs: Sequence[Belief], tz: tzinfo) -> dict[str, list[Belief]]:
    days: dict[str, list[Belief]] = defaultdict(list)
    for b in beliefs:
        days[b.recorded_at.astimezone(tz).date().isoformat()].append(b)
    return days


async def recent(
    store: Store, judge: Extractor, rel: RelationshipId, now: datetime, tz: tzinfo
) -> Proposed:
    """Group the memories of each of the last RECENT_DAYS days, for the nightly run."""
    since = now - timedelta(days=RECENT_DAYS)
    fresh = [b for b in store.user_beliefs(rel) if b.recorded_at >= since]
    total = await repick(store, judge, rel, now)
    for day in _by_day(fresh, tz).values():
        got = await propose(store, judge, rel, day, now)
        total = Proposed(total.groups + got.groups, total.cost_usd + got.cost_usd)
    return total


async def everything(
    store: Store, judge: Extractor, rel: RelationshipId, now: datetime, tz: tzinfo
) -> Proposed:
    """Every day's memories, then the whole store at once for repeats across days."""
    current = store.user_beliefs(rel)
    total = await repick(store, judge, rel, now)
    for day in [*_by_day(current, tz).values(), current]:
        got = await propose(store, judge, rel, day, now)
        total = Proposed(total.groups + got.groups, total.cost_usd + got.cost_usd)
    return total
