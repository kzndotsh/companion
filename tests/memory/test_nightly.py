from __future__ import annotations

from datetime import UTC, timedelta
from pathlib import Path

import pytest

import companion.memory.nightly as nightly_module
from companion.memory.nightly import LAST_RUN, MISSED_AFTER, missed, night
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


async def test_one_failing_step_does_not_skip_the_others_and_the_run_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    ran: list[str] = []

    async def check_fails(*_: object, **__: object) -> None:
        raise RuntimeError("judge down")

    async def group(*_: object, **__: object) -> None:
        ran.append("grouping")

    def routine(*_: object, **__: object) -> None:
        ran.append("routine")

    async def episodes(*_: object, **__: object) -> None:
        ran.append("episodes")

    monkeypatch.setattr(nightly_module, "nightly", check_fails)
    monkeypatch.setattr(nightly_module.merging, "recent", group)
    monkeypatch.setattr(nightly_module, "expire_routine", routine)
    monkeypatch.setattr(nightly_module, "write_closed", episodes)
    assert missed(store, REL, T0)
    failed = await night(store, None, REL, UTC, mode="shadow")  # type: ignore[arg-type]
    assert failed == ["memory check"]
    assert ran == ["grouping", "routine", "episodes"]
    assert store.setting(REL, LAST_RUN) is not None


def test_a_night_is_missed_only_after_more_than_a_day(tmp_path: Path) -> None:
    store = Store(tmp_path / "rel.sqlite")
    store.set_setting(REL, LAST_RUN, T0.isoformat(), T0)
    assert not missed(store, REL, T0 + timedelta(hours=20))
    assert missed(store, REL, T0 + MISSED_AFTER + timedelta(minutes=1))


async def test_a_night_where_every_step_failed_is_not_recorded_so_it_is_made_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "rel.sqlite")

    async def fails(*_: object, **__: object) -> None:
        raise RuntimeError("judge down")

    def fails_now(*_: object, **__: object) -> None:
        raise RuntimeError("store busy")

    monkeypatch.setattr(nightly_module, "nightly", fails)
    monkeypatch.setattr(nightly_module.merging, "recent", fails)
    monkeypatch.setattr(nightly_module, "expire_routine", fails_now)
    monkeypatch.setattr(nightly_module, "write_closed", fails)
    failed = await night(store, None, REL, UTC, mode="shadow")  # type: ignore[arg-type]
    assert len(failed) == 4
    assert store.setting(REL, LAST_RUN) is None
    assert missed(store, REL, T0)


async def test_with_the_memory_check_off_the_rest_of_the_night_still_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    ran: list[str] = []

    async def check(*_: object, **__: object) -> None:
        ran.append("check")

    async def step(*_: object, **__: object) -> None:
        ran.append("step")

    def routine(*_: object, **__: object) -> None:
        ran.append("routine")

    monkeypatch.setattr(nightly_module, "nightly", check)
    monkeypatch.setattr(nightly_module.merging, "recent", step)
    monkeypatch.setattr(nightly_module, "expire_routine", routine)
    monkeypatch.setattr(nightly_module, "write_closed", step)
    assert await night(store, None, REL, UTC, mode="off") == []  # type: ignore[arg-type]
    assert ran == ["step", "routine", "step"]
    assert store.setting(REL, LAST_RUN) is not None
