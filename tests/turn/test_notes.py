from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.turn.floor import HOLD_NOTE
from companion.core.turn.game import NOTE as GAME_NOTE
from companion.core.turn.ownup import NOTE as OWNED_NOTE
from companion.core.turn.questions import NOTE as QUESTION_NOTE
from companion.core.turn.questions import RUN
from companion.core.turn.quoted import Quoted
from companion.core.types import Speaker
from companion.features.curiosity.basics.logic import ASKED as ASKED_NAME
from companion.features.episodes.run import EPISODES_SHOWN
from companion.features.episodes.store import Episode
from companion.features.reminders.run import ASKED, SET, Read, reminder_offer
from companion.kit.current import Turn
from companion.kit.features import Offer, asking
from companion.kit.runtime import Runtime
from companion.store.sqlite.replay import replay_file
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from companion.turn.notes import SOURCES, Lookups, Moment, notes_for
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_a_failed_turn_uses_up_no_cap(store: Store) -> None:
    runtime = Runtime(store, Talker(fail=True), PREFIX, REL, judge=Judge())
    with pytest.raises(RuntimeError):
        await handle(runtime, SESSION, "hey, long day", "t", NOW)
    assert not store.decided_since(REL, ASKED_NAME, NOW - timedelta(days=1))
    talker = Talker()
    later = NOW + timedelta(minutes=1)
    await handle(Runtime(store, talker, PREFIX, REL, judge=Judge()), SESSION, "hey", "t", later)
    assert "what they like to be called" in talker.seen[0].card
    assert store.decided_since(REL, ASKED_NAME, NOW)


async def test_a_reply_to_one_of_its_messages_reaches_the_talker_quoted(store: Store) -> None:
    talker = Talker()
    runtime = Runtime(store, talker, PREFIX, REL, judge=Judge())
    await handle(
        runtime, SESSION, "so cute", "t", NOW, quoted=Quoted("your call", Speaker.COMPANION)
    )
    await handle(runtime, SESSION, "and this", "t", NOW + timedelta(minutes=1))
    assert "> your call" in talker.seen[0].card
    assert "> your call" not in talker.seen[1].card
    assert "> your call" not in talker.seen[0].messages[-1].content


async def test_their_message_id_is_kept_with_its_turn_even_at_the_cap(store: Store) -> None:
    runtime = Runtime(store, Talker(), PREFIX, REL, judge=Judge())
    await handle(runtime, SESSION, "hey", "discord", NOW, message_id="u1")
    capped = Runtime(store, Talker(), PREFIX, REL, judge=Judge(), daily_cap_usd=0.0)
    await handle(capped, SESSION, "still there?", "discord", NOW, message_id="u2")
    first = store.turn_of_message(REL, "discord", "u1")
    second = store.turn_of_message(REL, "discord", "u2")
    assert first is not None
    assert second is not None
    assert first != second
    later = NOW + timedelta(minutes=1)
    said = {
        u.turn_id: u.text for u in store.history_before(REL, later, 10) if u.speaker is Speaker.USER
    }
    assert said[first] == "hey"
    assert said[second] == "still there?"


def test_notes_come_in_the_listed_order_and_writes_wait(store: Store) -> None:
    runtime = Runtime(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, "t1", NOW, [], "hi")  # type: ignore[arg-type]
    from companion.core.types import Frame  # noqa: PLC0415

    notes = notes_for(
        Moment(
            runtime,
            t,
            Frame.REAL,
            None,
            Lookups(found={"reminder": Read("[set]", SET, {})}),
            True,
            [],
        )
    )
    assert notes.lines[-1] == "[set]"
    assert HOLD_NOTE.text in notes.lines
    assert notes.after == ()  # not read as casual, so no name is asked and nothing is used up
    assert len({name for name, _ in SOURCES}) == len(SOURCES)


async def test_after_a_heavy_talk_and_a_gap_it_checks_in_once(store: Store) -> None:
    heavy = Runtime(store, Talker(), PREFIX, REL, judge=Judge(severity=2))
    await handle(heavy, SESSION, "i can't stop crying tonight", "t", NOW)
    soon = Talker()
    await handle(
        Runtime(store, soon, PREFIX, REL, judge=Judge()),
        SESSION,
        "hey",
        "t",
        NOW + timedelta(hours=1),
    )
    assert "heavy for them" not in soon.seen[0].card  # back too soon: no check-in yet
    later = Talker()
    await handle(
        Runtime(store, later, PREFIX, REL, judge=Judge()),
        SESSION,
        "hi",
        "t",
        NOW + timedelta(hours=11),
    )
    assert "heavy for them" in later.seen[0].card
    assert "what they like to be called" not in later.seen[0].card  # nothing else nudges
    again = Talker()
    await handle(
        Runtime(store, again, PREFIX, REL, judge=Judge()),
        SESSION,
        "morning",
        "t",
        NOW + timedelta(hours=16),
    )
    assert "heavy for them" not in again.seen[0].card  # once per heavy talk


class _Owning(Talker):
    async def reply(self, request: TalkerRequest) -> Reply:
        await super().reply(request)
        return Reply(text="oh, my bad, I mixed it up", model="fake", latency_ms=1)


async def test_after_it_owns_a_slip_the_next_turn_says_enough_after_the_history(
    store: Store, tmp_path: Path
) -> None:
    await handle(
        Runtime(store, _Owning(), PREFIX, REL, judge=Judge()),
        SESSION,
        "he's the main character",
        "t",
        NOW,
    )
    later = NOW + timedelta(minutes=1)
    talker = Talker()
    await handle(
        Runtime(store, talker, PREFIX, REL, judge=Judge()),
        SESSION,
        "this is a show about that",
        "t",
        later,
    )
    sent = talker.seen[0]
    assert sent.tail == OWNED_NOTE.text
    assert OWNED_NOTE.text not in sent.card  # in the system block it moved nothing
    turn = store.history_before(REL, later + timedelta(minutes=1), 4)[-2].turn_id
    assert replay_file(tmp_path / "rel.sqlite", turn).matched  # replay rebuilds what came after


class _Asking(Talker):
    async def reply(self, request: TalkerRequest) -> Reply:
        await super().reply(request)
        return Reply(text="ooh, which one?", model="fake", latency_ms=1)


@pytest.mark.parametrize(("severity", "noted"), [(0, True), (2, False)])
async def test_after_a_run_of_questions_the_next_turn_asks_none_unless_it_is_serious(
    store: Store, severity: int, *, noted: bool
) -> None:
    for i in range(RUN):
        runtime = Runtime(store, _Asking(), PREFIX, REL, judge=Judge())
        await handle(runtime, SESSION, f"hey {i}", "t", NOW + timedelta(minutes=i))
    talker = Talker()
    runtime = Runtime(store, talker, PREFIX, REL, judge=Judge(severity=severity))
    await handle(runtime, SESSION, "a movie", "t", NOW + timedelta(minutes=RUN))
    assert (talker.seen[0].tail == QUESTION_NOTE.text) == noted
    assert QUESTION_NOTE.text not in talker.seen[0].card


async def test_in_a_game_of_questions_it_asks_the_next_one_and_no_run_note_stops_it(
    store: Store,
) -> None:
    for i, said in enumerate(["hey", "ask me anything", "the locals, mostly"]):
        runtime = Runtime(store, _Asking(), PREFIX, REL, judge=Judge())
        await handle(runtime, SESSION, said, "t", NOW + timedelta(minutes=i))
    talker = Talker()
    runtime = Runtime(store, talker, PREFIX, REL, judge=Judge())
    await handle(runtime, SESSION, "what about you", "t", NOW + timedelta(minutes=3))
    assert talker.seen[0].tail == GAME_NOTE.text  # not the question-run note


@pytest.mark.parametrize("mode", ["on", "shadow"])
async def test_recent_times_reach_the_talker_only_when_on_and_the_log_says_which(
    store: Store, mode: str
) -> None:
    await handle(Runtime(store, Talker(), PREFIX, REL, judge=Judge()), SESSION, "hey", "t", NOW)
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
    runtime = Runtime(store, talker, PREFIX, REL, judge=Judge(), episodes=mode)
    await handle(runtime, SESSION, "hi again", "t", later)
    assert (gist in talker.seen[0].card) == (mode == "on")
    turn = store.history_before(REL, later + timedelta(minutes=1), 4)[-2].turn_id
    [logged] = [d for d in store.decisions_for_turn(REL, turn) if d.has_key(EPISODES_SHOWN)]
    assert ("not sent" in logged.reason) == (mode == "shadow")


async def test_a_hung_look_up_is_left_out_at_the_deadline_and_a_failing_one_too(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio  # noqa: PLC0415
    import time  # noqa: PLC0415

    import companion.turn.notes as notes  # noqa: PLC0415

    async def hangs(*_: object) -> str | None:
        await asyncio.sleep(30)
        return "[set]"

    async def fails(*_: object) -> bool:
        raise RuntimeError("judge down")

    async def tastes(*_: object) -> tuple[str, ...]:
        return ("rainy days",)

    from companion.kit.features import Feature  # noqa: PLC0415

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
    runtime = Runtime(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, "t1", NOW, [], "hi")  # type: ignore[arg-type]
    from companion.core.types import Frame  # noqa: PLC0415

    began = time.monotonic()
    got = await notes.look(runtime, t, Frame.REAL, None, None)
    assert time.monotonic() - began < 2
    assert dict(got.found) == {"lore": ("rainy days",)}  # the failing and the hung are left out


def test_a_note_that_asks_says_so_and_a_reminder_set_does_not(store: Store) -> None:
    runtime = Runtime(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, "t1", NOW, [], "hi")  # type: ignore[arg-type]
    from companion.core.types import Frame  # noqa: PLC0415

    m = Moment(runtime, t, Frame.REAL, None, Lookups(), True, [])
    when = reminder_offer(m, Read("[ask when]", ASKED, {}, asks=True), {})
    told = reminder_offer(m, Read("[set]", SET, {}), {})
    assert asking({"reminder": when})
    assert not asking({"reminder": told})
    assert not asking({"game": Offer(asks=True)})  # an empty offer asks nothing
