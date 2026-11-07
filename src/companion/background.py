"""Everything that runs beside the chat while the bot is up, as jobs (`kit/jobs.py`) the daemon
starts with one loop: the features' own (`Feature.jobs`), the initiative timer, the night's memory
work and the daily backup. Which run is each switch's own choice; none has a loop of its own."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from companion import backups
from companion.core import switch as sw
from companion.core.clock import local_zone, utc_now
from companion.kit.features import Feature, Outlet, Round
from companion.kit.jobs import Every, Job
from companion.kit.runtime import Runtime
from companion.memory import nightly
from companion.paths import Paths
from companion.registry import FEATURES

INITIATIVE_TICK_SECONDS = 900


def initiative(c: Runtime, features: Sequence[Feature] = FEATURES) -> Job | None:
    """The timer that looks at open loops, times away and its own reasons to reach out (ADR 0021),
    in shadow mode recording and sending nothing. Each feature's steps (`Feature.reaching`) run in
    the order of `Kind` (`core/reachout.py`), the one place the precedence is stated."""
    if not c.on(sw.INITIATIVE):
        return None
    moves = sorted((m for f in features if f.reaching for m in f.reaching(c)), key=lambda m: m.rank)

    async def tick() -> None:
        reach = Round(utc_now(), local_zone())
        for move in moves:
            await move.run(reach)

    return Job("initiative", tick, Every(INITIATIVE_TICK_SECONDS))


def daily_backup(paths: Paths, into: Path) -> Job:
    """A snapshot once a day while the bot runs, besides the one at every start."""

    async def snapshot() -> None:
        await asyncio.to_thread(backups.back_up_quietly, paths, "daily", utc_now(), into)

    return Job("backups", snapshot, Every(backups.EVERY_SECONDS), capped=False)


def jobs(c: Runtime, outlet: Outlet, paths: Paths, into: Path) -> list[Job]:
    """Every job the bot runs, over the platform it is on."""
    own = [job for f in FEATURES if f.jobs for job in f.jobs(c, outlet)]
    rest = (initiative(c), daily_backup(paths, into), nightly.job(c))
    return [*own, *(job for job in rest if job is not None)]
