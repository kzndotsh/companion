"""`companion reminders`: the repeating ones they asked for (J50), with their state, how often and
when the next one goes, then every reminder soonest first and what became of it. `--cancel ID`
drops a pending reminder or stops a series; it is recorded, never deleted."""

from __future__ import annotations

from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.features.reminders.logic import Reminder, Series, Standing
from companion.features.reminders.run import stop
from companion.features.reminders.series import every_words
from companion.store.sqlite.store import Store


def _next(s: Series, every: list[Reminder]) -> str:
    pending = [r for r in every if r.series_id == s.id and r.state == "pending"]
    if pending:
        return f"next {pending[0].local_wall}"
    return "next when they write again" if s.state is Standing.PAUSED else "none"


def _cancel(store: Store, rel: RelationshipId, prefix: str) -> str:
    pending = [r for r in store.reminders(rel) if r.state == "pending" and r.id.startswith(prefix)]
    live = [
        s for s in store.series(rel) if s.state is not Standing.STOPPED and s.id.startswith(prefix)
    ]
    if len(pending) + len(live) != 1:
        found = len(pending) + len(live)
        return f"{found} pending reminders or series start with {prefix!r}; need exactly one\n"
    if live:
        stop(store, live[0], "the owner stopped it", utc_now())
        return f"stopped: {live[0].thing}, {every_words(live[0].repeat)}\n"
    store.reminder_event(pending[0].id, "cancelled", "the owner cancelled it", utc_now())
    return f"cancelled: {pending[0].thing}\n"


def run(db: Path, relationship: str, *, cancel: str | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        if cancel:
            return _cancel(store, rel, cancel)
        every, series = store.reminders(rel), store.series(rel)
        if not every and not series:
            return "no reminders\n"
        lines = [
            f"{s.id[:8]}  {s.state:7} {s.kind:8} {s.thing}: {every_words(s.repeat)}"
            f"  ({_next(s, every)})\n  {s.quote}"
            for s in series
        ]
        if lines:
            lines = ["repeating:", *lines, "", "reminders:"]
        lines += [
            f"{r.id[:8]}  {r.local_wall} {r.zone}  {r.state:9} {r.kind:8} {r.thing}"
            + (f"  (#{r.seq} of {r.series_id[:8]})" if r.series_id else "")
            + f"\n  {r.quote}"
            for r in every
        ]
        return "\n".join(lines) + "\n"
    finally:
        store.close()
