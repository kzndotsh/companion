"""The calendar's candidate: the one occasion today holds (their own dates from memory first), sent
after the history when the picker brings it up (`turn/mention.py`), where a note about the day was
used 12 of 12 times and the date alone 0 of 12 (2026-10-25)."""

from __future__ import annotations

from datetime import datetime, time

from companion.core.clock import named_zone
from companion.core.turn.mentions import MentionCandidate, Rank
from companion.core.types import Frame, Json, RelationshipId
from companion.features.calendar.logic import (
    LOOKBACK,
    OFFERED,
    REGION,
    Dated,
    How,
    Kind,
    Occasion,
    note,
    occasions,
    pick,
    their_dates,
    when,
)
from companion.kit.features import Feature, Moment
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


_RANK = {Kind.THEIRS: Rank.THEIRS, Kind.RELATIONSHIP: Rank.US}


def rank(o: Occasion) -> Rank:
    """A lead-up waits behind any day itself; a day of theirs comes first."""
    return Rank.LEAD_UP if o.how is How.LEAD_UP else _RANK.get(o.kind, Rank.DAY)


def calendar_candidate(m: Moment, found: object) -> MentionCandidate | None:
    """The occasion today holds (their own dates from memory first), never one offered in the
    last few days; nothing when switched off. The picker decides whether it is brought up."""
    del found
    c, t = m.c, m.t
    if not c.calendar:
        return None
    zone = named_zone()
    local = t.now.astimezone(zone)
    today = local.date()
    first = c.store.first_message_at(c.rel)
    since = datetime.combine(today - LOOKBACK, time.min, tzinfo=zone)
    offered = {str(d.get("occasion")) for _, d in c.store.calendar_offered(c.rel, since)}
    met = first.astimezone(zone).date() if first else None
    o = pick(occasions(today, REGION, met, theirs(c.store, c.rel)), offered)
    if o is None:
        return None
    detail = _detail(o, local)
    reason = f"calendar: offered {o.name} ({o.how.value.replace('_', ' ')}, {detail['when']})"
    return MentionCandidate(rank(o), note(o, today), True, OFFERED, o.name, detail, reason)


# Holidays, cultural days, their own dates and the relationship's (`COMPANION_CALENDAR`, on unless
# off): a candidate for the one thing brought up when they write.
CALENDAR = Feature("calendar", mention=calendar_candidate)
