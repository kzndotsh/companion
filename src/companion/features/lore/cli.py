"""`companion lore`: the companion's own lore (ADR 0020): its views labelled a taste, newest first,
with the words it said, and how its other views are sorted. Retire one with
`companion retire ID`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.features.lore.logic import lore
from companion.features.lore.run import label_views
from companion.kit.services import Services
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        views = store.self_beliefs(rel)
        kinds = store.view_kinds(rel)
    finally:
        store.close()
    tastes = lore(views, kinds)
    lines = [f'{b.id[:8]}  {b.claim}\n    "{b.evidence[0].quote}"' for b in reversed(tastes)]
    counts = Counter(kinds[b.id] for b in views if b.id in kinds)
    sorted_out = ", ".join(f"{n} {k}" for k, n in counts.most_common())
    unlabelled = sum(b.id not in kinds for b in views)
    tail = f"\n{len(views)} views: {sorted_out or 'none labelled'}; {unlabelled} not labelled yet"
    return ("\n".join(lines) if lines else "no lore yet") + tail + " (companion lore --label)\n"


async def label_now(x: Services, *, again: bool = False) -> str:
    """Label its views that have no kind yet (or all of them, `again`), for `companion lore`."""
    done = await label_views(x.store, x.judge, x.rel, utc_now(), batches=10, again=again)
    return f"labelled {done.labelled}, {done.left} left, ${done.cost_usd:.4f}\n"
