from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.types import Json
from companion.features.reminders.logic import Kind, Standing
from companion.features.reminders.run import CANCELLED, SET
from companion.store.sqlite.store import Store
from tests.features.reminders.test_run import Reminding, ask_slots, reasons, say
from tests.turn.test_mood_loop import NOW, REL

# NOW is Monday 19 Oct 2026, 17:00 UTC: 13:00 in New York


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    monkeypatch.setenv("TZ", "America/New_York")
    return Store(tmp_path / "rel.sqlite")


def _every_day(**kw: Json) -> dict[str, Json]:
    return ask_slots(repeats=True, every="day", **kw)


async def test_a_daily_reminder_sets_a_series_and_its_first_one(store: Store) -> None:
    judge = Reminding(_every_day(thing="take my meds", hour=8, ampm="pm"))
    card = await say(store, judge, "remind me every night at 8pm to take my meds")
    assert "remind them about take my meds, every day at 8:00 pm" in card
    assert "the first one is tonight at 8:00 pm" in card
    [series] = store.series(REL)
    assert (series.kind, series.state, series.repeat.rule) == (
        Kind.REMINDER,
        Standing.ACTIVE,
        "daily",
    )
    [first] = store.reminders(REL)
    assert (first.series_id, first.seq, first.state) == (series.id, 1, "pending")
    assert first.due_at == datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
    assert SET in reasons(store)


async def test_a_weekly_one_falls_on_its_day(store: Store) -> None:
    slots = ask_slots(repeats=True, every="friday", thing="the bins", hour=7, ampm="am")
    card = await say(store, Reminding(slots), "remind me every friday at 7am about the bins")
    assert "every Friday at 7:00 am" in card
    [first] = store.reminders(REL)
    assert first.local_wall == "2026-10-23 07:00"


async def test_a_morning_greeting_with_no_time_says_when_they_start_their_day(store: Store) -> None:
    slots = _every_day(kind="greeting", thing="good morning", part="morning")
    card = await say(store, Reminding(slots), "can you tell me good morning every day?")
    assert "around when they usually start their day" in card
    assert "the first one is tomorrow morning" in card
    assert "9:00" not in card
    [first] = store.reminders(REL)
    assert first.local_wall == "2026-10-20 09:00"  # under three days of messages: nine


async def test_a_repeating_reminder_with_no_time_asks_what_time(store: Store) -> None:
    card = await say(
        store, Reminding(_every_day(thing="stretch")), "remind me every day to stretch"
    )
    assert "but what time" in card
    assert store.series(REL) == []


async def test_a_cancel_naming_a_series_stops_it_and_its_pending_one(store: Store) -> None:
    await say(
        store,
        Reminding(_every_day(thing="take my meds", hour=8, ampm="pm")),
        "remind me every night at 8pm to take my meds",
    )
    await say(
        store,
        Reminding(ask_slots(hour=9, ampm="pm", thing="call mum")),
        "remind me at 9pm to call mum",
        NOW + timedelta(minutes=1),
    )
    gone = Reminding(ask_slots(ask="cancel", thing="the daily meds reminder"))
    card = await say(store, gone, "cancel the daily meds reminder", NOW + timedelta(minutes=2))
    assert "remind them about take my meds every day" in card
    [series] = store.series(REL)
    assert series.state is Standing.STOPPED
    assert {r.thing: r.state for r in store.reminders(REL)} == {
        "take my meds": "cancelled",
        "call mum": "pending",
    }
    assert CANCELLED in reasons(store)


async def test_stop_saying_good_morning_stops_the_greeting(store: Store) -> None:
    slots = _every_day(kind="greeting", thing="good morning", part="morning")
    await say(store, Reminding(slots), "say good morning to me every day")
    gone = Reminding(ask_slots(ask="cancel", kind="greeting", thing="saying good morning"))
    await say(store, gone, "you can stop saying good morning", NOW + timedelta(minutes=2))
    assert [s.state for s in store.series(REL)] == [Standing.STOPPED]
    assert [r.state for r in store.reminders(REL)] == ["cancelled"]
