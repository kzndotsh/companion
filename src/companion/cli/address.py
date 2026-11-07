"""`companion address`: how they want to be referred to, pinned in every turn's card.

`--set TEXT` records it (an empty text clears it); without it, shows what is set. Settings are
append-only, so every earlier value stays in the log."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.turn.address import KEY, address_note
from companion.core.types import RelationshipId
from companion.kit.command import Command, Group, db_args, emit, target
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, value: str | None, now: datetime | None = None) -> str:
    rel = RelationshipId(relationship)
    with Store(db) as store:
        if value is not None:
            store.set_setting(rel, KEY, value.strip(), now or utc_now())
        current = store.setting(rel, KEY)
    note = address_note(current)
    return f"pinned in every card:\n  {note}" if note else "nothing set; nothing is pinned"


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--set", dest="value", metavar="TEXT", help="record it; an empty text clears it")
    db_args(p)


COMMANDS = (
    Command(
        "address",
        Group.DAYS,
        "how they want to be referred to, pinned in every card",
        lambda a: emit(run(*target(a), a.value)),
        _args,
    ),
)
