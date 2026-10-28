"""`companion episodes`: the times they spent together (J12, shadow), oldest first, with the line
written about each. `--write` writes the ones not written yet (a model call)."""

from __future__ import annotations

from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.types import RelationshipId
from companion.features.episodes.run import write_closed
from companion.kit.services import Services
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        found = store.episodes(RelationshipId(relationship))
    finally:
        store.close()
    if not found:
        return "no episodes written yet (companion episodes --write)\n"
    zone = local_zone()
    lines: list[str] = []
    for e in found:
        start, end = e.start_at.astimezone(zone), e.end_at.astimezone(zone)
        marks = f"  [{', '.join(e.firsts)}]" if e.firsts else ""
        lines.append(
            f"{start:%a %d %b %H:%M}-{end:%H:%M}  {e.kind:8} {e.messages:4} msgs{marks}\n  {e.gist}"
        )
    return "\n".join(lines) + "\n"


async def write_now(x: Services) -> str:
    """Write a record of every finished stretch of chat that has none, for `companion episodes`."""
    done = await write_closed(x.store, x.judge, x.rel, utc_now())
    return f"wrote {done.written} episodes, ${done.cost_usd:.4f}\n"
