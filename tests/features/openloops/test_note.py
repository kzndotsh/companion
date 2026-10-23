from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from companion.core.basics import name_belief
from companion.core.types import Frame, Speaker, TurnId, Utterance, UtteranceId
from companion.features.openloops.logic import LoopState, OpenLoop
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "sam, and the vet is tomorrow",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    s.append_utterance(said)
    s.insert_belief(name_belief(said, "Sam", "b1", said.at))
    s.add_open_loop(
        OpenLoop(
            "vet",
            REL,
            "the vet visit",
            "the vet is tomorrow",
            said.id,
            NOW - timedelta(hours=1),
            0,
            said.at,
        )
    )
    return s


async def _say(store: Store, judge: Judge, at: datetime, text: str = "hey hey") -> str:
    talker = Talker()
    await handle(Conversation(store, talker, PREFIX, REL, judge=judge), SESSION, text, "test", at)
    return talker.seen[0].card


async def test_a_due_loop_is_offered_once_a_day_at_most_twice(store: Store) -> None:
    assert "the vet visit" in await _say(store, Judge(), NOW)
    assert store.open_loops(REL)[0].state is LoopState.ASKED
    assert "the vet visit" not in await _say(store, Judge(), NOW + timedelta(hours=2))
    assert "the vet visit" in await _say(store, Judge(), NOW + timedelta(days=1, minutes=1))
    assert "the vet visit" not in await _say(store, Judge(), NOW + timedelta(days=2, minutes=2))


async def test_a_serious_turn_gets_no_loop_note(store: Store) -> None:
    assert "the vet visit" not in await _say(store, Judge(severity=2), NOW, "i had a rough day")
    assert store.open_loops(REL)[0].state is LoopState.OPEN
