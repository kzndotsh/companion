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
from companion.features.episodes.run import EPISODES_SHOWN
from companion.features.episodes.store import Episode
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

    notes = notes_for(
        Moment(convo, t, Frame.REAL, None, Lookups(found={"reminder": "[set]"}), True, [])
    )
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


@pytest.mark.parametrize("mode", ["on", "shadow"])
async def test_recent_times_reach_the_talker_only_when_on_and_the_log_says_which(
    store: Store, mode: str
) -> None:
    await Conversation(store, Talker(), PREFIX, REL, judge=Judge()).handle(SESSION, "hey", "t", NOW)
    [first, last] = store.history_before(REL, NOW + timedelta(hours=1), 4)
    gist = "A quiet chat that ended warm."
    store.add_episode(
        REL,
        Episode(
            "e1", first.id, last.id, first.at, last.at, 2, "everyday", 0.0, 0, (), gist, "p", NOW
        ),
    )
    later = NOW + timedelta(hours=5)
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, judge=Judge(), episodes=mode)
    await convo.handle(SESSION, "hi again", "t", later)
    assert (gist in talker.seen[0].card) == (mode == "on")
    turn = store.history_before(REL, later + timedelta(minutes=1), 4)[-2].turn_id
    [logged] = [d for d in store.decisions_for_turn(REL, turn) if d.has_key(EPISODES_SHOWN)]
    assert ("not sent" in logged.reason) == (mode == "shadow")


async def test_a_hung_look_up_is_left_out_at_the_deadline_and_a_failing_one_too(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio  # noqa: PLC0415
    import time  # noqa: PLC0415

    import companion.loops.notes as notes  # noqa: PLC0415

    async def hangs(*_: object) -> str | None:
        await asyncio.sleep(30)
        return "[set]"

    async def fails(*_: object) -> bool:
        raise RuntimeError("judge down")

    async def tastes(*_: object) -> tuple[str, ...]:
        return ("rainy days",)

    from companion.loops.features import Feature  # noqa: PLC0415

    monkeypatch.setattr(notes, "LOOK_SECONDS", 0.2)
    monkeypatch.setattr(
        notes,
        "FEATURES",
        (
            Feature("lore", look=tastes),
            Feature("topic", look=fails),
            Feature("reminder", look=hangs),
        ),
    )
    convo = Conversation(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, "t1", NOW, [], "hi")  # type: ignore[arg-type]
    from companion.core.types import Frame  # noqa: PLC0415

    began = time.monotonic()
    got = await notes.look(convo, t, Frame.REAL, None, None)
    assert time.monotonic() - began < 2
    assert dict(got.found) == {"lore": ("rainy days",)}  # the failing and the hung are left out
