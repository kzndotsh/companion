"""The hold on reaching out first after a risk turn, as each gate reads it from the store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.crisis import HOLD_KEY, HOLD_REASON
from companion.core.types import RelationshipId, SessionId, TraceId, TurnId
from companion.features.reach.logic import Dial
from companion.features.reach.run import Reacher, holds
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def _holds(store: Store, at: datetime) -> bool:
    """The shared gate every reach-out asks (its own reasons, plans and nudges, ADR 0023)."""
    held = holds(store, REL, (at, UTC), Reacher(Dial.WARM, None))
    return held is not None and held.why == HOLD_REASON


@pytest.mark.parametrize(("hours", "held"), [(1, True), (23, True), (25, False)])
def test_every_reach_out_gate_holds_for_a_day_after_a_risk_turn(
    tmp_path: Path, hours: int, *, held: bool
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    assert not _holds(store, NOW)
    Recorder(store, REL, SessionId("s"), TurnId("t"), TraceId("t"), NOW).decide(HOLD_KEY)
    assert _holds(store, NOW + timedelta(hours=hours)) is held
    store.close()
