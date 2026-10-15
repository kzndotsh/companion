"""`companion beliefs`: what it currently believes about you, with the quote behind each."""

from __future__ import annotations

from pathlib import Path

from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        found = store.current_beliefs(RelationshipId(relationship))
    finally:
        store.close()
    if not found:
        return "no beliefs yet\n"
    lines: list[str] = []
    for b in sorted(found, key=lambda x: (x.kind, x.valid_from)):
        quote = b.evidence[0].quote
        lines.append(
            f"[{b.kind}/{b.provenance}] conf {b.confidence:.2f} sens {b.sensitivity}  {b.claim}"
            f'\n    "{quote}"'
        )
    return "\n".join(lines) + f"\n\n{len(found)} current beliefs\n"
