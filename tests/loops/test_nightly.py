from __future__ import annotations

from datetime import UTC, timedelta
from pathlib import Path

import pytest
from tests.conftest import REL, T0

import companion.loops.nightly as nightly_module
from companion.loops.nightly import LAST_RUN, MISSED_AFTER, missed, night
from companion.store.sqlite.store import Store


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
