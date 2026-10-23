"""`companion reminders`: the reminders they asked for (J50), soonest first, and what became of
each. `--cancel ID` drops a pending one; it is recorded, never deleted."""

from __future__ import annotations

from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, *, cancel: str | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        every = store.reminders(rel)
        if cancel:
            found = [r for r in every if r.state == "pending" and r.id.startswith(cancel)]
            if len(found) != 1:
                return f"{len(found)} pending reminders start with {cancel!r}; need exactly one\n"
            store.reminder_event(found[0].id, "cancelled", "the owner cancelled it", utc_now())
            return f"cancelled: {found[0].thing}\n"
        if not every:
            return "no reminders\n"
        lines = [
            f"{r.id[:8]}  {r.local_wall} {r.zone}  {r.state:9} {r.kind:8} {r.thing}\n  {r.quote}"
            for r in every
        ]
        return "\n".join(lines) + "\n"
    finally:
        store.close()
