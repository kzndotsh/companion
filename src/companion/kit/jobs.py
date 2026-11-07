"""Background work as data: a job is what to run and when, and one loop runs every job the same
way. A feature declares the jobs it has (`Feature.jobs` in `kit/features.py`) and the daemon starts
each; none writes its own while, sleep and except."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta

from companion.core.clock import local_zone, utc_now
from companion.kit.runtime import Runtime
from companion.kit.spendcap import over_cap


@dataclass(frozen=True, slots=True)
class Every:
    """Run once this many seconds after the last run, the first after the same wait."""

    seconds: float


@dataclass(frozen=True, slots=True)
class Daily:
    """Run once a day at this local hour. `catch_up` says, at the start, whether the last run was
    missed while the bot was down; if so one runs `catch_up_after` after the start."""

    hour: int
    catch_up: Callable[[], bool] | None = None
    catch_up_after: timedelta = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class Job:
    """One piece of background work. Named for its log lines (`companion.<name>`); `capped` jobs are
    skipped while today's spend is at the daily cap, and a job that costs nothing runs anyway."""

    name: str
    run: Callable[[], Awaitable[None]]
    when: Every | Daily
    capped: bool = True


def _until(hour: int) -> float:
    """Seconds from now to the next local `hour`:00."""
    now = utc_now().astimezone(local_zone())
    nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def keep_running(c: Runtime, job: Job) -> None:
    """Run `job` for as long as the bot does: the one policy for every job. A run that fails is
    logged and tried again at the next time; a capped job's run is skipped at the cap."""
    log = logging.getLogger(f"companion.{job.name}")

    async def once() -> None:
        if job.capped and over_cap(c.store, c.rel, c.daily_cap_usd, utc_now()) is not None:
            log.debug("daily spend cap reached; skipped")
            return
        try:
            await job.run()
        except Exception:
            log.exception("%s failed; will try again next time", job.name)

    match job.when:
        case Every(seconds):
            while True:
                await asyncio.sleep(seconds)
                await once()
        case Daily(hour, catch_up, after):
            if catch_up is not None and catch_up():
                await asyncio.sleep(after.total_seconds())
                await once()
            while True:
                await asyncio.sleep(_until(hour))
                await once()
