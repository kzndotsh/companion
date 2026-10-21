from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from tests.loops.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker

from companion.core.basics import ASKED as ASKED_NAME
from companion.core.floor import HOLD_NOTE
from companion.loops.fast import Conversation
from companion.loops.notes import SOURCES, Lookups, Moment, notes_for
from companion.loops.turn import Turn
from companion.store.sqlite.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_a_failed_turn_uses_up_no_cap(store: Store) -> None:
    convo = Conversation(store, Talker(fail=True), PREFIX, REL, judge=Judge())
    with pytest.raises(RuntimeError):
        await convo.handle(SESSION, "hey, long day", "t", NOW)
    assert not store.decided_since(REL, ASKED_NAME, NOW - timedelta(days=1))
    talker = Talker()
    later = NOW + timedelta(minutes=1)
    await Conversation(store, talker, PREFIX, REL, judge=Judge()).handle(SESSION, "hey", "t", later)
    assert "what they like to be called" in talker.seen[0].card
    assert store.decided_since(REL, ASKED_NAME, NOW)


def test_notes_come_in_the_listed_order_and_writes_wait(store: Store) -> None:
    convo = Conversation(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, "t1", NOW, [], "hi")  # type: ignore[arg-type]
    from companion.core.types import Frame  # noqa: PLC0415

    notes = notes_for(Moment(convo, t, Frame.REAL, None, Lookups(reminder="[set]"), True, []))
    assert notes.lines[-1] == "[set]"
    assert HOLD_NOTE.text in notes.lines
    assert notes.after == ()  # not read as casual, so no name is asked and nothing is used up
    assert len({name for name, _ in SOURCES}) == len(SOURCES)
