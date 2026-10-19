"""`companion flags`: what you marked as wrong, with the command that rebuilds each turn."""

from __future__ import annotations

import uuid
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import Favorite, FavoriteId, RelationshipId
from companion.store.sqlite.store import Store


def to_favorite(db: Path, relationship: str, id_prefix: str) -> str:
    """Take back a flag that was meant as a favourite: the flag is withdrawn (never deleted) and the
    same turn becomes a favourite with the same note."""
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        matches = [
            f
            for f in store.flags(rel)
            if f.id.startswith(id_prefix) or f.turn_id.startswith(id_prefix)
        ]
        if len(matches) != 1:
            return f"{len(matches)} flags match {id_prefix!r}; give more of the flag or turn id\n"
        flag, now = matches[0], utc_now()
        store.withdraw_flag(flag.id, "moved to a favourite by the owner", now)
        store.add_favorite(
            Favorite(FavoriteId(uuid.uuid4().hex), rel, flag.turn_id, flag.note, now)
        )
    finally:
        store.close()
    return f"moved to favourites: {flag.note}\n"


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
