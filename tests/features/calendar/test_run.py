from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.types import Frame, Speaker, TurnId, Utterance, UtteranceId
from companion.features.calendar.logic import DAY_NOTE, OFFERED, US_NOTE
from companion.features.calendar.run import calendar_offer
from companion.loops.conversation import Conversation
from companion.loops.current import Turn
from companion.loops.features import Lookups, Moment, Offer
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.features.marks.test_run import CALM, HEAVY
from tests.turn.test_mood_loop import PREFIX, REL, SESSION, Judge, Talker

HALLOWEEN = datetime(2026, 10, 31, 16, 0, tzinfo=UTC)  # noon in New York
NOTE = DAY_NOTE.render(name="Halloween")
QUIET = {"name": Offer(), "check-in": Offer()}


@pytest.fixture(autouse=True)
def _new_york(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "America/New_York")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _tail(
    store: Store,
    now: datetime,
    *,
    heard: object = CALM,
    frame: Frame = Frame.REAL,
    so_far: dict[str, Offer] | None = None,
    on: bool = True,
) -> Offer:
    convo = Conversation(store, Talker(), PREFIX, REL, calendar=on)
    t = Turn(SESSION, TurnId("t1"), now, [], "hey, what's up")
    m = Moment(convo, t, frame, heard, Lookups(), False, [])  # type: ignore[arg-type]
    return calendar_offer(m, None, so_far if so_far is not None else QUIET)


def test_on_a_casual_turn_the_day_goes_after_the_history_and_nowhere_else(store: Store) -> None:
    offer = _tail(store, HALLOWEEN)
    assert offer.tail == (NOTE,)
    assert offer.lines == ()
    assert len(offer.after) == 1
    assert not _tail(store, HALLOWEEN, heard=HEAVY).tail
    assert not _tail(store, HALLOWEEN, frame=Frame.PLAY).tail
    assert not _tail(store, HALLOWEEN, on=False).tail
    asked = QUIET | {"game": Offer(tail=("[ask the next one]",))}
    assert not _tail(store, HALLOWEEN, so_far=asked).tail
    assert not _tail(store, HALLOWEEN - timedelta(days=5)).tail  # an ordinary day


def test_a_hundred_days_since_the_first_message_comes_before_the_day(store: Store) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId("u0"),
            REL,
            SESSION,
            TurnId("t0"),
            Speaker.USER,
            "hi",
            Frame.REAL,
            "test",
            HALLOWEEN - timedelta(days=100),
        )
    )
    assert _tail(store, HALLOWEEN).tail == (US_NOTE.render(span="a hundred days"),)


async def test_offered_once_a_day_and_logged_only_when_the_turn_is_stored(store: Store) -> None:
    async def say(text: str, at: datetime, talker: Talker | None = None) -> Talker:
        talker = talker or Talker()
        await handle(
            Conversation(store, talker, PREFIX, REL, judge=Judge(), calendar=True),
            SESSION,
            text,
            "t",
            at,
        )
        return talker

    first = await say("hey", HALLOWEEN)
    assert NOTE not in first.seen[0].tail  # the first turn asks their name instead
    with pytest.raises(RuntimeError):
        await say("so", HALLOWEEN + timedelta(minutes=1), Talker(fail=True))
    assert not store.decided_since(REL, OFFERED, HALLOWEEN)  # a failed turn offered nothing
    second = await say("so, what's up", HALLOWEEN + timedelta(minutes=2))
    assert second.seen[0].tail == NOTE
    assert NOTE not in second.seen[0].card
    assert store.decided_since(REL, OFFERED, HALLOWEEN)
    third = await say("not much", HALLOWEEN + timedelta(minutes=3))
    assert NOTE not in third.seen[0].tail
