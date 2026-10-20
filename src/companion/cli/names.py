"""`companion names`: the things named in memory and the words that refer to each (fetch on
mention, shadow), with how many memories are about each and how often the card lacked them."""

from __future__ import annotations

from pathlib import Path

from companion.core.names import SHADOW, index
from companion.core.types import DecisionKind, RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        named = index(store.name_rows(rel), {b.id for b in store.user_beliefs(rel)})
        logged = [
            d for d in store.decisions_of_kind(rel, DecisionKind.POLICY) if d.reason == SHADOW
        ]
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
