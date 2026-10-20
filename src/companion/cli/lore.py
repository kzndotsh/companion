"""`companion lore`: the companion's own lore (ADR 0020): its views labelled a taste, newest first,
with the words it said, and how its other views are sorted. Retire one with
`companion retire ID`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from companion.core.lore import lore
from companion.core.types import RelationshipId
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
