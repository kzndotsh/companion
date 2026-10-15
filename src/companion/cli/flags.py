"""`companion flags`: what you marked as wrong, with the command that rebuilds each turn."""

from __future__ import annotations

from pathlib import Path

from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        found = store.flags(RelationshipId(relationship))
    finally:
        store.close()
    if not found:
        return "no flags yet\n"
    lines = [f"{f.at:%Y-%m-%d %H:%M}  {f.kind:<9} {f.turn_id}  {f.note}" for f in found]
    return "\n".join(lines) + "\n\nreplay one: companion replay <turn_id> --db <db>\n"
