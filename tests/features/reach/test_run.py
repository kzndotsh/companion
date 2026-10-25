from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reach.logic import DROPPED, HELD, WOULD_SEND, Dial, Kind
from companion.features.reach.run import Reacher, tick_reach
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)  # 3 PM, a usual hour on the baseline
WHEN = (NOW, UTC)


class Drafter:
    def __init__(self, message: str) -> None:
        self.message = message
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"message": self.message}, "fake", 0.0001, 3)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(store: Store, at: datetime, uid: str = "u1", speaker: Speaker = Speaker.USER) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId(uid),
            REL,
            SessionId("s"),
            TurnId(uid),
            speaker,
            "off to bed, night!",
            Frame.REAL,
            "test",
            at,
        )
    )


def _companion_messages(store: Store) -> int:
    return sum(
        1
        for u in store.history_before(REL, NOW + timedelta(days=1), 100)
        if u.speaker is Speaker.COMPANION
    )


def _keys(store: Store, kind: DecisionKind, key: str) -> int:
    return sum(1 for d in store.decisions_of_kind(REL, kind) if d.has_key(key))


async def test_a_shadow_tick_records_a_would_send_and_sends_nothing(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))  # past the 12-hour baseline pause
    drafter = Drafter("missed you a little today 🙂 how's the bread coming along?")
    reacher = Reacher(Dial.WARM, drafter)
    row = await tick_reach(store, REL, WHEN, reacher)
    assert row is not None
    assert (row.kind, row.mode, row.draft) == (Kind.MISSING, "shadow", drafter.message)
    assert row.detail["dial"] == "warm"
    assert isinstance(row.detail["rhythm"], dict)
    assert _keys(store, DecisionKind.INITIATE, WOULD_SEND) == 1
    assert _companion_messages(store) == 0  # nothing was sent or stored as said
    # The next tick: they have not written since, so it waits for them, without a paid call.
    again = await tick_reach(store, REL, (NOW + timedelta(hours=6), UTC), reacher)
    assert again is None
    assert drafter.calls == 1
    held = [d for d in store.decisions_of_kind(REL, DecisionKind.DO_NOTHING) if d.has_key(HELD)]
    assert [(d.detail or {}).get("hold") for d in held] == ["the last one is unanswered"]


async def test_no_paid_call_is_made_unless_every_check_passes(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("thinking of you")
    night = NOW.replace(hour=1)
    _said(store, night - timedelta(hours=14), "u0")
    assert await tick_reach(store, REL, (night, UTC), Reacher(Dial.WARM, drafter)) is None
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.OFF, drafter)) is None
    assert drafter.calls == 0
    assert store.own_reach_outs(REL) == []


async def test_a_plan_or_a_nudge_this_tick_goes_first(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("hey you")
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter), Kind.PLAN) is None
    assert drafter.calls == 0


async def test_a_needy_draft_is_dropped_and_recorded(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("you've been quiet all day, everything okay?")
    reacher = Reacher(Dial.WARM, drafter)
    assert await tick_reach(store, REL, WHEN, reacher) is None
    rows = store.own_reach_outs(REL)
    assert [(r.mode, r.draft) for r in rows] == [("dropped", "")]
    assert rows[0].detail["drafted"] == drafter.message
    assert _keys(store, DecisionKind.DO_NOTHING, DROPPED) == 1
    assert _keys(store, DecisionKind.INITIATE, WOULD_SEND) == 0
    # A dropped draft is not tried again within six hours.
    assert await tick_reach(store, REL, (NOW + timedelta(hours=1), UTC), reacher) is None
    assert drafter.calls == 1


async def test_the_initiative_command_shows_the_rhythm_the_share_and_the_would_sends(
    tmp_path: Path,
) -> None:
    from companion.cli import initiative  # noqa: PLC0415

    store = Store(tmp_path / "rel.sqlite")
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("how's the bread coming along?")
    await tick_reach(store, REL, WHEN, Reacher(Dial.NORMAL, drafter))
    await tick_reach(store, REL, (NOW + timedelta(hours=6), UTC), Reacher(Dial.NORMAL, drafter))
    store.close()
    out = initiative.run(tmp_path / "rel.sqlite", "rel", NOW + timedelta(hours=7))
    assert "COMPANION_REACH normal" in out
    assert "1 conversations in two weeks, 5% theirs and 95% baseline" in out
    assert "share it started: 1 of 2" in out
    assert "missing them" in out and drafter.message in out
    assert "1  the last one is unanswered" in out
