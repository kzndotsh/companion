"""`companion flags`: what you marked as wrong, with the command that rebuilds each turn."""

from __future__ import annotations

import argparse
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.ids import new_id
from companion.core.types import Favorite, FavoriteId, RelationshipId
from companion.kit.command import Command, Group, db_args, emit, target
from companion.store.sqlite.store import Store


def to_favorite(db: Path, relationship: str, id_prefix: str) -> str:
    """Take back a flag that was meant as a favourite: the flag is withdrawn (never deleted) and the
    same turn becomes a favourite with the same comment."""
    rel = RelationshipId(relationship)
    with Store(db) as store:
        matches = [
            f
            for f in store.flags(rel)
            if f.id.startswith(id_prefix) or f.turn_id.startswith(id_prefix)
        ]
        if len(matches) != 1:
            return f"{len(matches)} flags match {id_prefix!r}; give more of the flag or turn id\n"
        flag, now = matches[0], utc_now()
        store.withdraw_flag(flag.id, "moved to a favourite by the owner", now)
        store.add_favorite(Favorite(FavoriteId(new_id()), rel, flag.turn_id, flag.comment, now))
    return f"moved to favourites: {flag.comment}\n"


def run(db: Path, relationship: str) -> str:
    with Store(db) as store:
        found = store.flags(RelationshipId(relationship))
    if not found:
        return "no flags yet\n"
    lines = [f"{f.at:%Y-%m-%d %H:%M}  {f.kind:<9} {f.turn_id}  {f.comment}" for f in found]
    return "\n".join(lines) + "\n\nreplay one: companion replay <turn_id> --db <db>\n"


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--to-fav", metavar="ID", help="move a flag (by flag or turn id) to favourites")
    db_args(p)


def _run(a: argparse.Namespace) -> int:
    if a.to_fav:
        return emit(to_favorite(*target(a), str(a.to_fav)))
    return emit(run(*target(a)))


COMMANDS = (Command("flags", Group.FLAGS, "list the turns you flagged", _run, _args),)
