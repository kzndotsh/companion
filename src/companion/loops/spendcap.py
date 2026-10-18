"""A daily spend cap, read from the spend ledger.

The cap is a number the owner sets and the model cannot change. It is checked before a turn and
before the memory step, so once today's spend reaches it nothing paid runs until the next local
day. A turn already in flight can overshoot by a few cents, since its cost is known only after it
answers.
"""

from __future__ import annotations

from datetime import datetime

from companion.core.clock import local_midnight
from companion.core.types import RelationshipId
from companion.prompts import get
from companion.store.sqlite.store import Store

NOTICE = get("messages/spend-cap").text
NOTICE_KEY = "spend.cap_notice_day"


def spent_today(store: Store, rel: RelationshipId, now: datetime) -> float:
    return sum(row[3] for row in store.spend_since(rel, local_midnight(now)))


def over_cap(store: Store, rel: RelationshipId, cap: float | None, now: datetime) -> float | None:
    """Today's spend when it has reached the cap, otherwise None. No cap means never."""
    if cap is None:
        return None
    spent = spent_today(store, rel, now)
    return spent if spent >= cap else None


def first_notice_today(store: Store, rel: RelationshipId, now: datetime) -> bool:
    """True once per local day, so the user is told about the cap once and not on every message."""
    day = local_midnight(now).date().isoformat()
    if store.setting(rel, NOTICE_KEY) == day:
        return False
    store.set_setting(rel, NOTICE_KEY, day, now)
    return True
