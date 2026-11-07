from __future__ import annotations

from pathlib import Path

from companion.background import initiative
from companion.core.reachout import Kind
from companion.kit.features import Feature, Move, Round
from companion.store.sqlite.store import Store
from tests.runtime import make_runtime
from tests.turn.test_mood_loop import PREFIX, REL, Talker


def _feature(name: str, kind: Kind | None, log: list[str], *, takes: bool = False) -> Feature:
    async def run(r: Round) -> None:
        log.append(f"{name}:{r.first.name if r.first else None}")
        if takes and r.first is None:
            r.first = kind

    return Feature(name, reaching=lambda c: (Move(kind, run),))


async def test_the_initiative_tick_runs_the_steps_in_kind_order_whatever_the_registry_order(
    tmp_path: Path,
) -> None:
    c = make_runtime(Store(tmp_path / "r.sqlite"), Talker(), PREFIX, REL)
    log: list[str] = []
    features = [
        _feature("own", Kind.KEPT, log),
        _feature("nudge", Kind.AWAY, log, takes=True),
        _feature("gate", None, log),
        _feature("plan", Kind.PLAN, log, takes=True),
    ]
    job = initiative(c, features)
    assert job is not None
    await job.run()
    assert log == ["gate:None", "plan:None", "nudge:PLAN", "own:PLAN"]


async def test_no_initiative_job_while_the_switch_is_off(tmp_path: Path) -> None:
    c = make_runtime(Store(tmp_path / "r.sqlite"), Talker(), PREFIX, REL, initiative="off")
    assert initiative(c, []) is None
