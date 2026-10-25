"""The calendar's note: on a casual turn, the one occasion today holds (their own dates from memory
first), sent after the history,
where a note about the day was used 12 of 12 times and the date alone 0 of 12 (2026-10-25). Logged
with the occasion once the turn is stored, so a failed turn offers nothing."""

from __future__ import annotations

from datetime import datetime, time

from companion.core.clock import named_zone
from companion.core.types import Frame, Json, RelationshipId
from companion.features.calendar.logic import (
    LOOKBACK,
    OFFERED,
    REGION,
    Dated,
    Occasion,
    note,
    occasions,
    pick,
    their_dates,
    when,
)
from companion.loops.current import decide
from companion.loops.features import Feature, Moment, Offer, Offered, asking, quiet
from companion.store.sqlite.store import Store


def _detail(o: Occasion, today: datetime) -> dict[str, Json]:
    return {
        "occasion": o.key,
        "name": o.name,
        "day": o.day.isoformat(),
        "kind": o.kind.value,
        "how": o.how.value,
        "when": when(o, today.date()),
        "region": REGION,
    }


def theirs(store: Store, rel: RelationshipId) -> tuple[Dated, ...]:
    """Their yearly dates from what memory holds about them: said for real, never sensitive."""
    memories = store.user_beliefs(rel)
    return their_dates([(b.claim, b.sensitivity) for b in memories if b.frame is Frame.REAL])


def calendar_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """Nothing when switched off, on a turn that is not casual or quiet, or when another note asks
    them something; else the picked occasion, never one offered already."""
    del found
    c, t = m.c, m.t
    if not c.calendar or not quiet(m, so_far) or asking(so_far):
        return Offer()
    zone = named_zone()
    local = t.now.astimezone(zone)
    today = local.date()
    first = c.store.first_message_at(c.rel)
    since = datetime.combine(today - LOOKBACK, time.min, tzinfo=zone)
    offered = {str(d.get("occasion")) for _, d in c.store.calendar_offered(c.rel, since)}
    met = first.astimezone(zone).date() if first else None
    o = pick(occasions(today, REGION, met, theirs(c.store, c.rel)), offered)
    if o is None:
        return Offer()
    detail = _detail(o, local)
    reason = f"calendar: offered {o.name} ({o.how.value.replace('_', ' ')}, {detail['when']})"
    return Offer(
        tail=(note(o, today),),
        after=(lambda: decide(c, t, OFFERED, detail, reason=reason),),
        asks=True,
    )


# Holidays, cultural days and the relationship's dates (`COMPANION_CALENDAR`, on unless off).
CALENDAR = Feature("calendar", note=calendar_offer)
