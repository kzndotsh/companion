from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from companion.core.types import Frame, Speaker, TurnId, Utterance, UtteranceId
from companion.features.reminders.logic import Kind, Part, Repeat, Series, Standing
from companion.features.reminders.run import (
    PAUSED,
    RESUMED,
    SKIPPED,
    STUCK_GONE,
    deliver_due,
    schedule,
    stop,
)
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from tests.features.reminders.test_run import Writer
from tests.turn.test_mood_loop import PREFIX, REL, SESSION

TZ = ZoneInfo("America/New_York")
SET_AT = datetime(2026, 10, 19, 13, 0, tzinfo=TZ)  # a Monday


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    monkeypatch.setenv("TZ", "America/New_York")
    return Store(tmp_path / "rel.sqlite")


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=TZ)


def _series(store: Store, kind: Kind = Kind.GREETING, repeat: Repeat | None = None) -> Series:
    s = Series(
        f"s-{kind}",
        REL,
        kind,
        "good morning" if kind is Kind.GREETING else "take my meds",
        "q",
        repeat or Repeat(None, None, Part.MORNING),
        "America/New_York",
        TurnId("t0"),
        SET_AT,
    )
    store.add_series(s)
    schedule(Runtime(store, Writer(), PREFIX, REL), s, SET_AT, TZ)
    return s


def _they_wrote(store: Store, at: datetime) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId(f"u-{at.timestamp()}"),
            REL,
            SESSION,
            TurnId(f"t-{at.timestamp()}"),
            Speaker.USER,
            "morning!",
            Frame.REAL,
            "t",
            at,
        )
    )


async def _tick(store: Store, now: datetime, talker: Writer | None = None) -> list[str]:
    out: list[str] = []

    async def send(text: str) -> None:
        out.append(text)

    c = Runtime(store, talker or Writer("morning you ☀️"), PREFIX, REL)
    await deliver_due(c, send, SESSION, now, SET_AT, channel="telegram")
    return out


def _states(store: Store) -> list[tuple[str, str]]:
    return [(r.local_wall, r.state) for r in store.reminders(REL)]


async def test_a_greeting_goes_in_its_own_voice_and_the_next_day_is_made(store: Store) -> None:
    _series(store)
    talker = Writer("morning you ☀️")
    assert await _tick(store, _at(20, 9, 0), talker) == ["morning you ☀️"]
    assert "good morning" in talker.seen[0].tail
    assert "not opened or worded like the ones you sent on earlier days" in talker.seen[0].tail
    assert _states(store) == [("2026-10-20 09:00", "sent"), ("2026-10-21 09:00", "pending")]


async def test_a_morning_greeting_is_skipped_when_they_wrote_first(store: Store) -> None:
    _series(store)
    _they_wrote(store, _at(20, 7, 30))
    assert await _tick(store, _at(20, 9, 0)) == []
    assert _states(store) == [("2026-10-20 09:00", "skipped"), ("2026-10-21 09:00", "pending")]
    assert store.decisions_with_key(REL, SKIPPED)


async def test_a_daily_reminder_goes_even_when_they_just_wrote(store: Store) -> None:
    _series(store, Kind.REMINDER, Repeat(None, time(8, 30)))
    _they_wrote(store, _at(20, 8, 29))
    assert await _tick(store, _at(20, 8, 30), Writer("meds time 💊")) == ["meds time 💊"]
    assert _states(store) == [("2026-10-20 08:30", "sent"), ("2026-10-21 08:30", "pending")]


async def test_three_unanswered_greetings_pause_it_and_their_next_message_resumes_it(
    store: Store,
) -> None:
    s = _series(store)
    for day in (20, 21, 22):
        assert await _tick(store, _at(day, 9, 0)) == ["morning you ☀️"]
    assert [x.state for x in store.series(REL)] == [Standing.PAUSED]
    assert [state for _, state in _states(store)] == ["sent", "sent", "sent"]
    assert await _tick(store, _at(23, 9, 0)) == []
    assert store.decisions_with_key(REL, PAUSED)
    _they_wrote(store, _at(23, 12, 0))
    assert await _tick(store, _at(23, 12, 1)) == []
    assert [x.state for x in store.series(REL)] == [Standing.ACTIVE]
    assert _states(store)[-1] == ("2026-10-24 09:00", "pending")
    assert store.decisions_with_key(REL, RESUMED)
    assert store.series(REL)[0].id == s.id


async def test_one_pending_occurrence_however_often_the_scheduler_runs(store: Store) -> None:
    s = _series(store)
    c = Runtime(store, Writer(), PREFIX, REL)
    for _ in range(3):
        schedule(c, s, SET_AT + timedelta(minutes=1), TZ)
    await _tick(store, SET_AT + timedelta(minutes=2))
    await _tick(store, SET_AT + timedelta(minutes=2))
    assert _states(store) == [("2026-10-20 09:00", "pending")]


async def test_a_stopped_series_makes_no_more(store: Store) -> None:
    s = _series(store)
    stop(store, s, "they asked to stop it", SET_AT + timedelta(minutes=5))
    assert await _tick(store, _at(20, 9, 0)) == []
    assert _states(store) == [("2026-10-20 09:00", "cancelled")]


async def test_a_series_stopped_while_its_greeting_was_sending_makes_no_next_one(
    store: Store,
) -> None:
    s = _series(store)

    async def send(text: str) -> None:
        del text
        stop(store, s, "they asked to stop it", _at(20, 9, 0))

    c = Runtime(store, Writer("morning ☀️"), PREFIX, REL)
    await deliver_due(c, send, SESSION, _at(20, 9, 0), SET_AT, channel="telegram")
    assert _states(store) == [("2026-10-20 09:00", "sent")]


async def test_one_cut_off_mid_send_is_let_go_not_resent_and_its_series_goes_on(
    store: Store,
) -> None:
    _series(store, Kind.REMINDER, Repeat(None, time(8, 30)))
    [first] = store.reminders(REL)
    assert store.claim_reminder(first.id, _at(20, 8, 30))  # a crash right after the claim
    assert await _tick(store, _at(20, 8, 35)) == []
    assert _states(store) == [("2026-10-20 08:30", "claimed")]
    assert await _tick(store, _at(20, 8, 45)) == []
    assert _states(store) == [("2026-10-20 08:30", "expired"), ("2026-10-21 08:30", "pending")]
    assert store.decisions_with_key(REL, STUCK_GONE)
