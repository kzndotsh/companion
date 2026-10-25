"""`companion calendar`: the occasions in the next 30 days, lead-ups included, and what was offered
in the last 30, from the decisions."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

from companion.core.clock import named_zone, utc_now
from companion.core.types import RelationshipId
from companion.features.calendar.logic import REGION, How, occasions, when
from companion.features.calendar.run import theirs
from companion.store.sqlite.store import Store

DAYS = 30


def run(db: Path, relationship: str, *, now: datetime | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    zone = named_zone()
    local = (now or utc_now()).astimezone(zone)
    today = local.date()
    try:
        first = store.first_message_at(rel)
        since = datetime.combine(today - timedelta(days=DAYS), time.min, tzinfo=zone)
        offered = store.calendar_offered(rel, since)
        dates = theirs(store, rel)
    finally:
        store.close()
    first_met = first.astimezone(zone).date() if first is not None else None
    known = ", ".join(f"{d.name} {d.month}/{d.day}" for d in dates) or "none"
    lines = [f"their dates from memory: {known}"]
    lines.append(f"the next {DAYS} days ({REGION}; first talked {first_met or 'not yet'}):")
    for ahead in range(DAYS):
        day = today + timedelta(days=ahead)
        for o in occasions(day, REGION, first_met, dates):
            what = f"{o.name} {when(o, day)}" if o.how is How.LEAD_UP else o.name
            kind = "lead-up" if o.how is How.LEAD_UP else o.kind.value
            lines.append(f"  {day:%Y-%m-%d %a}  {kind:12} {what}")
    lines.append(f"offered in the last {DAYS} days:")
    lines.extend(
        f"  {at.astimezone(zone):%Y-%m-%d %H:%M}  {d.get('how', '')!s:10}  {d.get('name')}"
        f" ({d.get('when')})"
        for at, d in offered
    )
    if not offered:
        lines.append("  nothing")
    return "\n".join(lines) + "\n"
