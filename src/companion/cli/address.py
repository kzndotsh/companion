"""`companion address`: how they want to be referred to, pinned in every turn's card.

`--set TEXT` records it (an empty text clears it); without it, shows what is set. Settings are
append-only, so every earlier value stays in the log."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.turn.address import KEY, address_note
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, value: str | None, now: datetime | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        if value is not None:
            store.set_setting(rel, KEY, value.strip(), now or utc_now())
        current = store.setting(rel, KEY)
    finally:
        store.close()
    note = address_note(current)
    return f"pinned in every card:\n  {note}" if note else "nothing set; nothing is pinned"
