"""The night's memory work: each step on its own, so one failing does not skip the rest, and the
time of the last full run kept, so a night the bot was down is made up when it starts again."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, tzinfo

from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId
from companion.features.episodes.run import write_closed
from companion.features.upkeep.merging import run as merging
from companion.features.upkeep.reread.run import nightly
from companion.features.upkeep.sort.run import expire_routine
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.nightly")
LAST_RUN = "nightly: last run"  # a setting: when every step was last tried
MISSED_AFTER = timedelta(hours=26)  # longer than this since the last run, a night was missed


def missed(store: Store, rel: RelationshipId, now: datetime) -> bool:
    """Whether a night was missed: never run, or not for longer than MISSED_AFTER."""
    last = store.setting(rel, LAST_RUN)
    return last is None or now - datetime.fromisoformat(last) > MISSED_AFTER


async def night(
    store: Store, judge: StructuredModel, rel: RelationshipId, zone: tzinfo, *, mode: str
) -> list[str]:
    """Run every step once, each on its own; the names of those that failed. The run is recorded
    when at least one step worked, so one step that keeps failing is tried again the next night,
    not in a loop, while a night where every step failed (the judge down) is made up at the next
    start."""

    async def check() -> None:
        await nightly(store, judge, rel, utc_now(), zone, mode=mode)

    async def group() -> None:
        await merging.recent(store, judge, rel, utc_now(), zone)

    async def routine() -> None:
        expire_routine(store, rel, utc_now())

    async def episodes() -> None:
        await write_closed(store, judge, rel, utc_now())

    # The re-read is the only step behind its switch; the rest of the night's work always runs.
    steps: tuple[tuple[str, Callable[[], Awaitable[None]]], ...] = (
        *((("re-read", check),) if mode != "off" else ()),
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
    if len(failed) < len(steps):
        store.set_setting(rel, LAST_RUN, utc_now().isoformat(), utc_now())
    return failed
