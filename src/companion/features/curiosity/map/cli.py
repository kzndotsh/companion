"""`companion map`: what it knows about them by part of their life and depth, the gap it would ask
about now, and the recent picks (J48). Writes nothing; `--label` labels new ones first."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.types import Depth, Domain, RelationshipId
from companion.features.curiosity.map.logic import ASKED, WOULD_ASK, pick_gap
from companion.features.curiosity.map.run import label_new
from companion.kit.services import Services
from companion.store.sqlite.store import Store

SHOWN_PICKS = 7


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        beliefs = store.user_beliefs(rel)
        labels = store.belief_labels(rel)
        picks = store.decisions_with_key(rel, WOULD_ASK) + store.decisions_with_key(rel, ASKED)
    finally:
        store.close()
    cells = Counter((labels[b.id].domain, labels[b.id].depth) for b in beliefs if b.id in labels)
    head = "".join(f"{d.value:>10}" for d in Depth)
    out = [f"{'':10}{head}     total"]
    for dom in Domain:
        row = [cells[(dom, dep)] for dep in Depth]
        out.append(f"{dom.value:10}" + "".join(f"{n:>10}" for n in row) + f"{sum(row):>10}")
    unlabelled = sum(b.id not in labels for b in beliefs)
    out.append(f"\n{len(beliefs)} memories, {unlabelled} not labelled yet (companion map --label)")
    gap = pick_gap(beliefs, labels)
    out.append(gap.reason if gap else "map: nothing labelled yet")
    if picks:
        zone = local_zone()
        out.append("\nrecent picks (offered: the note was sent; shadow: only logged):")
        for d in sorted(picks, key=lambda d: d.at)[-SHOWN_PICKS:]:
            domain = (d.detail or {}).get("domain", "?")
            how = "offered" if d.has_key(ASKED) else "shadow"
            out.append(f"  {d.at.astimezone(zone):%a %d %b %H:%M}  {domain:10} {how}")
    return "\n".join(out)


async def label_now(x: Services) -> str:
    """Label memories that have no label yet, for `companion map --label`."""
    done = await label_new(x.store, x.judge, x.rel, utc_now(), batches=10)
    return f"labelled {done.labelled}, {done.left} left, ${done.cost_usd:.4f}\n"
