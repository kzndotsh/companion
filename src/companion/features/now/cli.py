"""`companion now`: their labelled messages of the last three days (something coming, leaving, back,
done), what is open now, and the notes it sent or would have sent."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.turn.now import KEY, from_decisions, open_now
from companion.core.types import RelationshipId
from companion.features.now.run import SENT, SHADOW
from companion.store.sqlite.store import Store

DAYS = 3


def run(db: Path, relationship: str, *, now: datetime | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    at = now or utc_now()
    since = at - timedelta(days=DAYS)
    try:
        said = from_decisions(store.decisions_with_key(rel, KEY, since))
        notes = [
            *store.decisions_with_key(rel, SENT, since),
            *store.decisions_with_key(rel, SHADOW, since),
        ]
    finally:
        store.close()
    zone = local_zone()
    lines = [f"labelled in the last {DAYS} days ({len(said)}):"]
    lines += [
        f"  {s.at.astimezone(zone):%m-%d %H:%M}  {s.label.phase:8} {s.label.what}" for s in said
    ]
    still = open_now(said, at)
    lines.append(f"open now: {', '.join(s.label.what for s in still) or 'nothing'}")
    lines.append(f"notes ({len(notes)}):")
    lines += [
        f"  {d.at.astimezone(zone):%m-%d %H:%M}  {'sent' if d.has_key(SENT) else 'shadow'}  "
        f"{(d.detail or {}).get('note', '')}"
        for d in sorted(notes, key=lambda d: d.at)
    ]
    return "\n".join(lines) + "\n"
