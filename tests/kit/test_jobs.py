from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta
from pathlib import Path

import pytest
from tests.runtime import make_runtime
from tests.turn.test_mood_loop import PREFIX, REL, Talker

from companion.core.clock import utc_now
from companion.core.spend import SpendEvent
from companion.kit.jobs import Every, Job, keep_running
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store


async def _run_for(c: Runtime, job: Job, seconds: float = 0.4) -> None:
    task = asyncio.create_task(keep_running(c, job))
    await asyncio.sleep(seconds)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def _count(into: list[int], *, fails: bool = False) -> Job:
    async def run() -> None:
        into.append(1)
        if fails:
            raise RuntimeError("model down")

    return Job("probe", run, Every(0.01), capped=True)


async def test_a_job_runs_again_after_its_interval(tmp_path: Path) -> None:
    c, ran = make_runtime(Store(tmp_path / "r.sqlite"), Talker(), PREFIX, REL), list[int]()
    await _run_for(c, _count(ran))
    assert len(ran) >= 2


async def test_a_job_that_fails_is_logged_and_tried_again(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    c, ran = make_runtime(Store(tmp_path / "r.sqlite"), Talker(), PREFIX, REL), list[int]()
    with caplog.at_level(logging.ERROR, logger="companion.probe"):
        await _run_for(c, _count(ran, fails=True))
    assert len(ran) >= 2
    assert "probe failed; will try again next time" in caplog.text


async def test_a_capped_job_waits_while_the_day_is_at_the_cap_and_a_free_one_does_not(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "r.sqlite")
    store.record_spend(REL, SpendEvent("talker", "m", 1.0), utc_now() - timedelta(seconds=1))
    c = make_runtime(store, Talker(), PREFIX, REL, daily_cap_usd=0.5)
    capped, free = list[int](), list[int]()
    await _run_for(c, _count(capped))
    await _run_for(c, Job("free", _count(free).run, Every(0.01), capped=False))
    assert capped == []
    assert len(free) >= 2
