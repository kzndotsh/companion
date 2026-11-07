"""The night's memory work (ADR 0019): the steps the features declare (`Feature.nightly`, in the
registry's order), each on its own so one failing does not skip the rest, and the time of the last
full run kept, so a night the bot was down is made up when it starts again."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.switch import Position
from companion.core.types import RelationshipId
from companion.kit.features import Feature
from companion.kit.jobs import Daily, Job
from companion.kit.runtime import Runtime
from companion.registry import FEATURES
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.nightly")
LAST_RUN = "nightly: last run"  # a setting: when every step was last tried
MISSED_AFTER = timedelta(hours=26)  # longer than this since the last run, a night was missed
NIGHTLY_HOUR = 4  # local time, when they are least likely to be chatting


def missed(store: Store, rel: RelationshipId, now: datetime) -> bool:
    """Whether a night was missed: never run, or not for longer than MISSED_AFTER."""
    last = store.setting(rel, LAST_RUN)
    return last is None or now - datetime.fromisoformat(last) > MISSED_AFTER


async def night(
    c: Runtime, judge: StructuredModel, features: Sequence[Feature] = FEATURES
) -> list[str]:
    """Run every step once, each on its own; the names of those that failed. A step behind a switch
    that is off is left out. The run is recorded when at least one step worked, so one step that
    keeps failing is tried again the next night, not in a loop, while a night where every step
    failed (the judge down) is made up at the next start."""
    steps = [
        f.nightly
        for f in features
        if f.nightly is not None
        and (f.nightly.switch is None or c.position(f.nightly.switch) is not Position.OFF)
    ]
    failed: list[str] = []
    for step in steps:
        try:
            await step.run(c, judge)
        except Exception:
            log.exception("nightly %s failed; the other steps still run", step.name)
            failed.append(step.name)
    if len(failed) < len(steps):
        c.store.set_setting(c.rel, LAST_RUN, utc_now().isoformat(), utc_now())
    return failed


def job(c: Runtime) -> Job | None:
    """The night's work once a night at NIGHTLY_HOUR, made up shortly after a start when the last
    night was missed. None when the runtime has no memory model."""
    judge = c.memory
    if judge is None:
        return None

    async def run() -> None:
        failed = await night(c, judge)
        if failed:
            log.warning("nightly: %s failed", ", ".join(failed))

    return Job("nightly", run, Daily(NIGHTLY_HOUR, lambda: missed(c.store, c.rel, utc_now())))
