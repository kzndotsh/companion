"""The night's memory work: each step on its own, so one failing does not skip the rest, and the
time of the last full run kept, so a night the bot was down is made up when it starts again."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, tzinfo

from companion.core.clock import utc_now
from companion.core.extractor import Extractor
from companion.core.types import RelationshipId
from companion.features.episodes.run import write_closed
from companion.loops import merging
from companion.loops.consolidate import nightly
from companion.loops.worth import expire_routine
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.nightly")
LAST_RUN = "nightly: last run"  # a setting: when every step was last tried
MISSED_AFTER = timedelta(hours=26)  # longer than this since the last run, a night was missed


def missed(store: Store, rel: RelationshipId, now: datetime) -> bool:
    """Whether a night was missed: never run, or not for longer than MISSED_AFTER."""
    last = store.setting(rel, LAST_RUN)
    return last is None or now - datetime.fromisoformat(last) > MISSED_AFTER


async def night(
    store: Store, judge: Extractor, rel: RelationshipId, zone: tzinfo, *, mode: str
) -> list[str]:
    """Run every step once, each on its own; the names of those that failed. The run is recorded
    either way, so a failing step is tried again the next night, not in a loop."""

    async def check() -> None:
        await nightly(store, judge, rel, utc_now(), zone, mode=mode)

    async def group() -> None:
        await merging.recent(store, judge, rel, utc_now(), zone)

    async def routine() -> None:
        expire_routine(store, rel, utc_now())

    async def episodes() -> None:
        await write_closed(store, judge, rel, utc_now())

    steps: tuple[tuple[str, Callable[[], Awaitable[None]]], ...] = (
        ("memory check", check),
        ("grouping", group),
        ("routine expiry", routine),
        ("episodes", episodes),
    )
    failed: list[str] = []
    for name, step in steps:
        try:
            await step()
        except Exception:
            log.exception("nightly %s failed; the other steps still run", name)
            failed.append(name)
    store.set_setting(rel, LAST_RUN, utc_now().isoformat(), utc_now())
    return failed
