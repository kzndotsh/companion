"""Restating memory from the whole ledger under the current extraction rules."""

from __future__ import annotations

from datetime import tzinfo

from companion.core.clock import utc_now
from companion.core.extractor import Extractor
from companion.core.types import RelationshipId
from companion.loops.curate import close
from companion.memory.slow import ReflectOptions, reflect_from
from companion.store.sqlite.store import Store


async def rebuild(
    store: Store, extractor: Extractor, rel: RelationshipId, tz: tzinfo | None = None
) -> str:
    """Restate every belief from the whole ledger under the current extraction rules.

    The old beliefs are closed only after every batch has succeeded, so a failure part-way leaves
    them in force. They stay on disk, closed, with the reason logged.
    """
    old = store.user_beliefs(rel)
    options = ReflectOptions(ignore=frozenset(b.id for b in old), tz=tz)
    start = None
    added = 0
    while True:
        result = await reflect_from(store, extractor, rel, start, options)
        if not result.ran:
            break
        added += result.accepted
        start = result.upto
    now = utc_now()
    for b in old:
        close(store, b, "replaced by a rebuild under improved extraction rules", now)
    return f"rebuilt: {added} beliefs added, {len(old)} replaced"
