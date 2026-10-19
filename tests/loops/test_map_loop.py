from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from tests.loops.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker

from companion.core.basics import name_belief
from companion.core.knowing import WOULD_ASK, Depth, Domain, Label
from companion.core.types import Frame, Speaker, TurnId, Utterance, UtteranceId
from companion.loops.fast import Conversation
from companion.store.sqlite.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "sam",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    s.append_utterance(said)
    named = name_belief(said, "Sam", "b1", said.at)
    s.insert_belief(named)
    s.add_belief_labels(REL, [Label(named.id, Domain.IDENTITY, Depth.SURFACE)], "m", "p", NOW)
    return s


async def _say(store: Store, judge: Judge, text: str = "lol ok", at: datetime = NOW) -> Talker:
    talker = Talker()
    await Conversation(store, talker, PREFIX, REL, judge=judge, mood="off").handle(
        SESSION, text, "test", at
    )
    return talker


def _picks(store: Store) -> list[str]:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=3), 50)}
    return [
        str((d.detail or {}).get("domain"))
        for t in turns
        for d in store.decisions_for_turn(REL, t)
        if d.reason == WOULD_ASK
    ]


async def test_a_casual_turn_logs_the_gap_once_a_day_and_sends_nothing(store: Store) -> None:
    talker = await _say(store, Judge())
    await _say(store, Judge(), at=NOW + timedelta(hours=1))
    assert _picks(store) == ["people"]
    assert "people" not in talker.seen[0].card
    await _say(store, Judge(), at=NOW + timedelta(days=1, minutes=1))
    assert _picks(store) == ["people", "people"]


async def test_a_serious_turn_picks_nothing(store: Store) -> None:
    await _say(store, Judge(severity=2), "my grandma died")
    assert _picks(store) == []


async def test_nothing_is_picked_while_it_still_asks_their_name(tmp_path: Path) -> None:
    store = Store(tmp_path / "fresh.sqlite")
    await _say(store, Judge())
    assert _picks(store) == []
