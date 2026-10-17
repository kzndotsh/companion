"""`companion spend`: what the paid calls cost, today and over the last week, by purpose."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, now: datetime | None = None) -> str:
    now = now or utc_now()
    zone = local_zone()
    midnight = datetime.combine(now.astimezone(zone).date(), time.min, tzinfo=zone)
    store = Store(db)
    try:
        today = store.spend_since(RelationshipId(relationship), midnight)
        week = store.spend_since(RelationshipId(relationship), midnight - timedelta(days=6))
    finally:
        store.close()
    if not week:
        return "no spend recorded yet\n"
    return "\n".join([*_block("today", today), "", *_block("last 7 days", week)]) + "\n"


def _block(title: str, rows: list[tuple[str, str, int, float]]) -> list[str]:
    total = sum(r[3] for r in rows)
    lines = [f"{title}: ${total:.4f} over {sum(r[2] for r in rows)} calls"]
    lines += [f"  {p:<14} {m:<34} {n:>5} calls  ${d:.4f}" for p, m, n, d in rows]
    return lines if rows else [f"{title}: nothing"]
