from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from companion.core.types import RelationshipId, TurnId
from companion.features.reminders import store
from companion.features.reminders.logic import Kind, Part, Reminder, Repeat, Series, Standing
from companion.lib.sqlite import db
from companion.store.sqlite.db import MIGRATIONS

REL = RelationshipId("r")
NOW = datetime(2026, 10, 26, 14, 0, tzinfo=UTC)


def _upto(conn: sqlite3.Connection, tmp: Path, last: int) -> None:
    folder = tmp / f"upto{last}"
    folder.mkdir()
    for entry in MIGRATIONS.iterdir():
        if entry.name.endswith(".sql") and int(entry.name.split("_")[0]) <= last:
            (folder / entry.name).write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
    db.migrate(conn, folder)


def test_reminders_set_before_series_existed_survive_the_migration(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "x.sqlite")
    _upto(conn, tmp_path, 34)
    conn.execute(
        "INSERT INTO reminders VALUES ('r1', 'r', 'reminder', 'the dog', 'q',"
        " '2026-10-20T00:00:00.000000+00:00', '2026-10-19 20:00', 'America/New_York', 't',"
        " '2026-10-19T17:00:00.000000+00:00')"
    )
    conn.execute(
        "INSERT INTO reminder_events (reminder_id, state, reason, at)"
        " VALUES ('r1', 'sent', 'sent by fake', '2026-10-20T00:00:00.000000+00:00')"
    )
    db.migrate(conn, MIGRATIONS)
    [r] = store.all_(conn, REL)
    assert (r.id, r.thing, r.state, r.series_id, r.seq) == ("r1", "the dog", "sent", None, None)
    assert r.state_at == datetime(2026, 10, 20, tzinfo=UTC)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def _series() -> Series:
    return Series(
        "s1",
        REL,
        Kind.GREETING,
        "good morning",
        "tell me good morning every day",
        Repeat(None, None, Part.MORNING),
        "America/New_York",
        TurnId("t"),
        NOW,
    )


def _occurrence(seq: int, rid: str) -> Reminder:
    due = NOW + timedelta(days=seq)
    return Reminder(
        rid, REL, Kind.GREETING, "good morning", "q", due, "", "x", TurnId("t"), NOW,
        series_id="s1", seq=seq,
    )  # fmt: skip


def test_the_same_occurrence_of_a_series_is_made_once(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "x.sqlite")
    db.migrate(conn, MIGRATIONS)
    store.add_series(conn, _series())
    assert store.add_occurrence(conn, _occurrence(1, "a"))
    assert not store.add_occurrence(conn, _occurrence(1, "b"))  # a second scheduler, same number
    assert [(r.id, r.state, r.seq) for r in store.all_(conn, REL)] == [("a", "pending", 1)]


def test_a_series_reads_back_with_its_newest_state(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "x.sqlite")
    db.migrate(conn, MIGRATIONS)
    store.add_series(conn, _series())
    fixed = Series(
        "s2", REL, Kind.REMINDER, "meds", "q", Repeat(4, time(20, 30)), "z", TurnId("t"), NOW
    )
    store.add_series(conn, fixed)
    store.series_event(conn, "s1", Standing.PAUSED, "3 sent since they last wrote", NOW)
    got = {s.id: s for s in store.all_series(conn, REL)}
    assert got["s1"].state is Standing.PAUSED
    assert got["s1"].repeat == Repeat(None, None, Part.MORNING)
    assert got["s2"].repeat == Repeat(4, time(20, 30))
    assert got["s2"].state is Standing.ACTIVE
