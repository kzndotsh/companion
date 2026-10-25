"""The hold on reaching out first after a risk turn, as each gate reads it from the store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.crisis import HOLD_KEY
from companion.core.types import RelationshipId, SessionId, TraceId, TurnId
from companion.features.nudges.run import _look as nudge_look  # pyright: ignore[reportPrivateUsage]
from companion.features.openloops.run import (
    _situation as loop_situation,  # pyright: ignore[reportPrivateUsage]
)
from companion.features.reach.logic import Dial
from companion.features.reach.run import Reacher, situation
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def _holds(store: Store, at: datetime) -> tuple[bool, bool, bool]:
    reach = situation(store, REL, (at, UTC), Reacher(Dial.WARM, None))[0].crisis
    return reach, loop_situation(store, REL, at, UTC).crisis, nudge_look(store, REL, at).crisis


@pytest.mark.parametrize(("hours", "held"), [(1, True), (23, True), (25, False)])
def test_every_reach_out_gate_holds_for_a_day_after_a_risk_turn(
    tmp_path: Path, hours: int, *, held: bool
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    assert _holds(store, NOW) == (False, False, False)
    Recorder(store, REL, SessionId("s"), TurnId("t"), TraceId("t"), NOW).decide(HOLD_KEY)
    assert _holds(store, NOW + timedelta(hours=hours)) == (held, held, held)
    store.close()
