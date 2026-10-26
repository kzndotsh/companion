from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from companion.core.types import TurnId
from companion.features.reminders import cli
from companion.features.reminders.logic import Kind, Part, Repeat, Series, Standing
from companion.features.reminders.run import schedule
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from tests.features.reminders.test_run import Writer
from tests.turn.test_mood_loop import PREFIX, REL

TZ = ZoneInfo("America/New_York")
SET_AT = datetime(2026, 10, 19, 13, 0, tzinfo=TZ)


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TZ", "America/New_York")
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    for sid, kind, thing, repeat in (
        ("aaaa1111", Kind.GREETING, "good morning", Repeat(None, None, Part.MORNING)),
        ("bbbb2222", Kind.REMINDER, "take my meds", Repeat(4, time(20))),
    ):
        s = Series(sid, REL, kind, thing, "q", repeat, "America/New_York", TurnId("t"), SET_AT)
        store.add_series(s)
        schedule(Conversation(store, Writer(), PREFIX, REL), s, SET_AT, TZ)
    store.close()
    return path


def test_the_list_shows_each_series_with_its_state_how_often_and_next(db: Path) -> None:
    out = cli.run(db, REL)
    assert "aaaa1111  active  greeting good morning: every morning, around when" in out
    assert "(next 2026-10-20 09:00)" in out
    assert "bbbb2222  active  reminder take my meds: every Friday at 8:00 pm" in out
    assert "(next 2026-10-23 20:00)" in out
    assert "(#1 of aaaa1111)" in out


def test_cancel_by_a_series_prefix_stops_it_and_its_pending_one(db: Path) -> None:
    assert cli.run(db, REL, cancel="bbbb") == "stopped: take my meds, every Friday at 8:00 pm\n"
    store = Store(db)
    try:
        states = {s.id: s.state for s in store.series(REL)}
        assert states == {"aaaa1111": Standing.ACTIVE, "bbbb2222": Standing.STOPPED}
        assert {r.thing: r.state for r in store.reminders(REL)} == {
            "good morning": "pending",
            "take my meds": "cancelled",
        }
    finally:
        store.close()
    assert "need exactly one" in cli.run(db, REL, cancel="bbbb")
