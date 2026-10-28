"""The one picker for what it brings up on its own, across plans and days (ADR 0023)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.turn.mentions import Rank
from companion.core.types import Frame, Speaker, TraceId, TurnId, Utterance, UtteranceId
from companion.features.calendar.logic import OFFERED
from companion.features.threads.logic import Thread, ThreadKind
from companion.features.threads.run import LOOP_OFFERED
from companion.kit.current import Turn
from companion.kit.features import Lookups, Moment, Offer
from companion.kit.record import Recorder
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.mention import MET, mention_note, read_met
from tests.features.calendar.test_run import CALM, HALLOWEEN, NOTE, QUIET, remember
from tests.features.threads.test_note import Meets
from tests.turn.test_mood_loop import PREFIX, REL, SESSION, Talker

BIRTHDAY = "The user's birthday is October 31."


@pytest.fixture(autouse=True)
def _new_york(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "America/New_York")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _turn(store: Store, minutes: int) -> tuple[str, ...]:
    """One casual turn's mention, its writes run as if the turn were stored."""
    runtime = Runtime(store, Talker(), PREFIX, REL, calendar=True)
    t = Turn(SESSION, TurnId(f"t{minutes}"), HALLOWEEN + timedelta(minutes=minutes), [], "hey")
    offer: Offer = mention_note(Moment(runtime, t, Frame.REAL, CALM, Lookups(), False, []), QUIET)
    for write in offer.after:
        write()
    return offer.lines + offer.tail


def _thread(store: Store, kind: ThreadKind, due_hours: int = 0) -> None:
    said = store.history_before(REL, HALLOWEEN, 1)[0]
    due = HALLOWEEN - timedelta(hours=due_hours)
    store.add_open_loop(
        Thread(kind.value, REL, "the thing", "q", said.id, due, 0, said.at, kind=kind)
    )


def _brought_up(store: Store) -> int:
    return sum(len(store.decisions_with_key(REL, k)) for k in (LOOP_OFFERED, OFFERED))


def test_their_birthday_is_marked_once_though_two_sources_know_it(store: Store) -> None:
    remember(store, "b1", BIRTHDAY)
    _thread(store, ThreadKind.CELEBRATE)
    assert _turn(store, 0)
    assert not _turn(store, 30)
    assert not _turn(store, 300)
    assert _brought_up(store) == 1


def test_a_morning_follow_up_never_holds_back_their_birthday(store: Store) -> None:
    remember(store, "b1", BIRTHDAY)
    morning = HALLOWEEN - timedelta(hours=3)
    Recorder(store, REL, SESSION, TurnId("m"), TraceId("m"), morning).decide(
        LOOP_OFFERED, {"rank": int(Rank.FOLLOW_UP), "about": "the vet"}
    )
    assert "their birthday" in "".join(_turn(store, 0))


def test_a_day_brought_up_holds_back_a_follow_up_the_same_day(store: Store) -> None:
    remember(store, "b0", "The user likes tea.")
    _thread(store, ThreadKind.FOLLOW_UP, due_hours=2)
    assert _turn(store, 0) == (NOTE,)  # Halloween before the follow-up
    assert not _turn(store, 60)
    assert _brought_up(store) == 1


async def test_how_they_met_a_day_is_read_like_a_plan(store: Store) -> None:
    _turn(store, 0)  # Halloween brought up on turn t0
    reply = Utterance(
        UtteranceId("r0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.COMPANION,
        "happy halloween! any plans?",
        Frame.REAL,
        "test",
        HALLOWEEN,
    )
    store.append_utterance(reply)
    runtime = Runtime(store, Talker(), PREFIX, REL, judge=Meets())
    then = HALLOWEEN + timedelta(minutes=2)
    t = Turn(SESSION, TurnId("t1"), then, [reply], "yes!! a costume party")
    await read_met(runtime, t, reply, None)
    met = store.decisions_with_key(REL, MET)
    assert [(d.detail or {}).get("about") for d in met] == ["Halloween"]
