from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker

from companion.core.turn.address import KEY as ADDRESS_KEY
from companion.core.types import (
    Depth,
    Domain,
    Frame,
    Label,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.curiosity.basics.logic import name_belief
from companion.features.curiosity.map.logic import ASKED
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle


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
    s.set_setting(REL, ADDRESS_KEY, "they/them", said.at)  # the basics known: no ask this turn
    s.add_belief_labels(REL, [Label(named.id, Domain.IDENTITY, Depth.SURFACE)], "m", "p", NOW)
    return s


async def _say(store: Store, judge: Judge, text: str = "lol ok", at: datetime = NOW) -> Talker:
    talker = Talker()
    await handle(
        Runtime(store, talker, PREFIX, REL, judge=judge, mood="off"), SESSION, text, "test", at
    )
    return talker


def _picks(store: Store) -> list[str]:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=5), 50)}
    return [
        str((d.detail or {}).get("domain"))
        for t in turns
        for d in store.decisions_for_turn(REL, t)
        if d.has_key(ASKED)
    ]


async def test_a_casual_turn_asks_about_the_gap_once_in_three_days(store: Store) -> None:
    first = await _say(store, Judge())
    later = await _say(store, Judge(), at=NOW + timedelta(days=2))
    assert _picks(store) == ["people"]
    assert "the people in their life" in first.seen[0].card
    assert "the people in their life" not in later.seen[0].card
    await _say(store, Judge(), at=NOW + timedelta(days=3, minutes=1))
    assert _picks(store) == ["people", "people"]


async def test_a_serious_turn_picks_nothing(store: Store) -> None:
    talker = await _say(store, Judge(severity=2), "my grandma died")
    assert _picks(store) == []
    assert "the people in their life" not in talker.seen[0].card


async def test_nothing_is_picked_while_it_still_asks_their_name(tmp_path: Path) -> None:
    store = Store(tmp_path / "fresh.sqlite")
    await _say(store, Judge())
    assert _picks(store) == []
