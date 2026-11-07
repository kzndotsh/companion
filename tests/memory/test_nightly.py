from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from companion.core import switch as sw
from companion.core.extractor import StructuredModel
from companion.kit.features import Feature, NightStep
from companion.kit.runtime import Runtime
from companion.memory.nightly import LAST_RUN, MISSED_AFTER, missed, night
from companion.registry import FEATURES
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0
from tests.runtime import make_runtime
from tests.turn.test_mood_loop import PREFIX, Talker


def _runtime(tmp_path: Path, **changes: object) -> Runtime:
    return make_runtime(Store(tmp_path / "rel.sqlite"), Talker(), PREFIX, REL, **changes)


def _step(
    name: str, ran: list[str], *, fails: bool = False, switch: sw.Switch | None = None
) -> Feature:
    async def run(c: Runtime, judge: StructuredModel) -> None:
        del c, judge
        ran.append(name)
        if fails:
            raise RuntimeError("judge down")

    return Feature(name, nightly=NightStep(name, run, switch))


async def test_one_failing_step_does_not_skip_the_others_and_the_run_is_kept(
    tmp_path: Path,
) -> None:
    c, ran = _runtime(tmp_path), list[str]()
    steps = [_step("re-read", ran, fails=True), _step("grouping", ran), _step("episodes", ran)]
    assert missed(c.store, REL, T0)
    assert await night(c, None, steps) == ["re-read"]  # type: ignore[arg-type]
    assert ran == ["re-read", "grouping", "episodes"]
    assert c.store.setting(REL, LAST_RUN) is not None


def test_a_night_is_missed_only_after_more_than_a_day(tmp_path: Path) -> None:
    store = Store(tmp_path / "rel.sqlite")
    store.set_setting(REL, LAST_RUN, T0.isoformat(), T0)
    assert not missed(store, REL, T0 + timedelta(hours=20))
    assert missed(store, REL, T0 + MISSED_AFTER + timedelta(minutes=1))


async def test_a_night_where_every_step_failed_is_not_recorded_so_it_is_made_up(
    tmp_path: Path,
) -> None:
    c, ran = _runtime(tmp_path), list[str]()
    steps = [_step(name, ran, fails=True) for name in ("a", "b", "c", "d")]
    assert len(await night(c, None, steps)) == 4  # type: ignore[arg-type]
    assert c.store.setting(REL, LAST_RUN) is None
    assert missed(c.store, REL, T0)


async def test_a_step_behind_a_switch_that_is_off_is_left_out_and_the_rest_of_the_night_runs(
    tmp_path: Path,
) -> None:
    c, ran = _runtime(tmp_path, reread="off"), list[str]()
    steps = [_step("re-read", ran, switch=sw.REREAD), _step("grouping", ran)]
    assert await night(c, None, steps) == []  # type: ignore[arg-type]
    assert ran == ["grouping"]
    assert c.store.setting(REL, LAST_RUN) is not None


def test_the_night_runs_the_registry_steps_in_the_order_of_the_upkeep_work() -> None:
    names = [f.nightly.name for f in FEATURES if f.nightly is not None]
    assert names == ["re-read", "grouping", "routine expiry", "episodes"]
