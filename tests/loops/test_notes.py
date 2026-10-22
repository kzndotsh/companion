from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from tests.loops.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker

from companion.core.basics import ASKED as ASKED_NAME
from companion.core.floor import HOLD_NOTE
from companion.core.ownup import NOTE as OWNED_NOTE
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.loops.fast import Conversation
from companion.loops.notes import SOURCES, Lookups, Moment, notes_for
from companion.loops.turn import Turn
from companion.store.sqlite.replay import replay_file
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


async def test_after_a_heavy_talk_and_a_gap_it_checks_in_once(store: Store) -> None:
    heavy = Conversation(store, Talker(), PREFIX, REL, judge=Judge(severity=2))
    await heavy.handle(SESSION, "i can't stop crying tonight", "t", NOW)
    soon = Talker()
    await Conversation(store, soon, PREFIX, REL, judge=Judge()).handle(
        SESSION, "hey", "t", NOW + timedelta(hours=1)
    )
    assert "heavy for them" not in soon.seen[0].card  # back too soon: no check-in yet
    later = Talker()
    await Conversation(store, later, PREFIX, REL, judge=Judge()).handle(
        SESSION, "hi", "t", NOW + timedelta(hours=11)
    )
    assert "heavy for them" in later.seen[0].card
    assert "what they like to be called" not in later.seen[0].card  # nothing else nudges
    again = Talker()
    await Conversation(store, again, PREFIX, REL, judge=Judge()).handle(
        SESSION, "morning", "t", NOW + timedelta(hours=16)
    )
    assert "heavy for them" not in again.seen[0].card  # once per heavy talk


class _Owning(Talker):
    async def reply(self, request: TalkerRequest) -> Reply:
        await super().reply(request)
        return Reply(text="oh, my bad, I mixed it up", model="fake", latency_ms=1)


async def test_after_it_owns_a_slip_the_next_turn_says_enough_after_the_history(
    store: Store, tmp_path: Path
) -> None:
    await Conversation(store, _Owning(), PREFIX, REL, judge=Judge()).handle(
        SESSION, "he's the main character", "t", NOW
    )
    later = NOW + timedelta(minutes=1)
    talker = Talker()
    await Conversation(store, talker, PREFIX, REL, judge=Judge()).handle(
        SESSION, "this is a show about that", "t", later
    )
    sent = talker.seen[0]
    assert sent.tail == OWNED_NOTE.text
    assert OWNED_NOTE.text not in sent.card  # in the system block it moved nothing
    turn = store.history_before(REL, later + timedelta(minutes=1), 4)[-2].turn_id
    assert replay_file(tmp_path / "rel.sqlite", turn).matched  # replay rebuilds what came after
