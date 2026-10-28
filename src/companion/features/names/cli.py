"""`companion names`: the things named in memory and the words that refer to each (fetch on
mention, shadow), with how many memories are about each and how often the card lacked them."""

from __future__ import annotations

from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.features.names.logic import SHADOW, index
from companion.features.names.run import read_names
from companion.kit.services import Services
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        named = index(store.name_rows(rel), {b.id for b in store.user_beliefs(rel)})
        logged = store.decisions_with_key(rel, SHADOW)
        left = len(store.user_beliefs(rel)) - len(store.names_read(rel))
    finally:
        store.close()
    if not named:
        return f"no names yet; {left} memories not read (companion names --read)\n"
    lines = [
        f"{len(n.beliefs):3}  {n.name}  ({', '.join(n.terms)})"
        for n in sorted(named, key=lambda n: (-len(n.beliefs), n.name.lower()))
    ]
    missed = sum(1 for d in logged if isinstance(d.detail, dict) and d.detail.get("would_add"))
    lines.append(
        f"\n{len(logged)} turns named something; on {missed} the card lacked a memory about it"
        f" (shadow). {left} memories not read yet."
    )
    return "\n".join(lines) + "\n"


async def read_now(x: Services) -> str:
    """List the names in memories not read yet, for `companion names --read`."""
    done = await read_names(x.store, x.judge, x.rel, utc_now(), batches=10)
    return (
        f"read {done.read} memories, {done.names} names, {done.left} left, ${done.cost_usd:.4f}\n"
    )
