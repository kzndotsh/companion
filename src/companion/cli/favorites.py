"""`companion favorites`: the turns you loved, with the command that rebuilds each one."""

from __future__ import annotations

from pathlib import Path

from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        found = store.favorites(RelationshipId(relationship))
    finally:
        store.close()
    if not found:
        return "no favorites yet\n"
    lines = [f"{f.at:%Y-%m-%d %H:%M}  {f.turn_id}  {f.note}" for f in found]
    return "\n".join(lines) + "\n\nreplay one: companion replay <turn_id> --db <db>\n"
