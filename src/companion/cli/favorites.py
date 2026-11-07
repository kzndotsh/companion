"""`companion favorites`: the turns you loved, with the command that rebuilds each one."""

from __future__ import annotations

from pathlib import Path

from companion.core.types import RelationshipId
from companion.kit.command import Group, plain
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    with Store(db) as store:
        found = store.favorites(RelationshipId(relationship))
    if not found:
        return "no favorites yet\n"
    lines = [f"{f.at:%Y-%m-%d %H:%M}  {f.turn_id}  {f.comment}" for f in found]
    return "\n".join(lines) + "\n\nreplay one: companion replay <turn_id> --db <db>\n"


COMMANDS = (plain("favorites", Group.FLAGS, "list the turns you loved", run),)
