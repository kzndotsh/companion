from __future__ import annotations

from pathlib import Path

from tests.conftest import T0

from companion.cli.initiative import run
from companion.core.reachout import OWN_HELD, PLAN_HELD
from companion.core.types import DecisionKind, RelationshipId
from companion.kit.record import Recorder
from companion.store.sqlite.store import Store

REL = RelationshipId("owner")


def test_every_kind_of_hold_is_listed_under_held(tmp_path: Path) -> None:
    db = tmp_path / "companion.sqlite"
    store = Store(db)
    rec = Recorder.fresh(store, REL, T0)
    rec.decide(PLAN_HELD, reason="plan hold text", kind=DecisionKind.DO_NOTHING)
    rec.decide(OWN_HELD, {"hold": "quiet"}, reason="own hold text", kind=DecisionKind.DO_NOTHING)
    store.close()
    held = run(db, REL, T0).split("held (")[1].split("stepped away")[0]
    assert "plan hold text" in held
    assert "own hold text" in held
