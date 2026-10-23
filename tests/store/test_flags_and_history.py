from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.replay import TurnRecord
from companion.core.types import Belief, Flag, FlagId, FlagKind, SessionId, TurnId, Utterance
from companion.lib.sqlite.db import connect
from companion.store.sqlite import flags, ledger, turns
from companion.store.sqlite.db import migrate
from tests.conftest import REL, T0


def test_history_before_crosses_sessions_and_keeps_order(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    from dataclasses import replace  # noqa: PLC0415

    a = utterance(text="yesterday", uid="a")
    b = replace(utterance(text="today", uid="b"), session_id=SessionId("other"))
    for u in (a, b):
        ledger.append_utterance(conn, u)
    got = ledger.history_before(conn, REL, b.at + timedelta(seconds=1), 10)
    assert [u.text for u in got] == ["yesterday", "today"]


def test_history_before_is_strict_and_limited(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    made = [utterance(text=f"m{i}", uid=f"u{i}") for i in range(5)]
    for u in made:
        ledger.append_utterance(conn, u)
    got = ledger.history_before(conn, REL, made[4].at, 2)
    assert [u.text for u in got] == ["m2", "m3"]


def _turn(conn: sqlite3.Connection, tid: str) -> TurnId:
    from companion.core.prompt.prefix import build_prefix  # noqa: PLC0415

    p = build_prefix("x " * 3000)
    turns.save_prefix(conn, p)
    turns.record_turn(
        conn, TurnRecord(TurnId(tid), REL, SessionId("s"), p.sha256, "", "0" * 64, None, T0)
    )
    return TurnId(tid)


def test_latest_turn_is_the_most_recent(conn: sqlite3.Connection) -> None:
    assert turns.latest_turn(conn, REL) is None
    _turn(conn, "t1")
    assert turns.latest_turn(conn, REL) == "t1"


def test_flags_round_trip_and_are_append_only(conn: sqlite3.Connection) -> None:
    t = _turn(conn, "t1")
    f = Flag(FlagId("f1"), REL, t, FlagKind.FORGOT, "knew I'm the builder", T0)
    flags.add_flag(conn, f)
    assert flags.list_flags(conn, REL) == [f]
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE flags SET note = 'x'")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM flags")


def test_flag_must_point_at_a_real_turn(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        flags.add_flag(conn, Flag(FlagId("f"), REL, TurnId("nope"), FlagKind.OFF, "", T0))


def test_unknown_flag_kind_is_rejected_by_the_database(conn: sqlite3.Connection) -> None:
    t = _turn(conn, "t1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO flags VALUES ('f', ?, ?, 'meh', '', ?)", (REL, t, T0.isoformat()))


def test_migrations_are_idempotent(tmp_path: object) -> None:
    from pathlib import Path  # noqa: PLC0415

    c = connect(Path(str(tmp_path)) / "x.sqlite")
    migrate(c)
    migrate(c)
    c.close()


def test_last_support_is_the_newest_evidence_time(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.types import Evidence, UtteranceId  # noqa: PLC0415
    from companion.store.sqlite import beliefs  # noqa: PLC0415

    old, new = (
        utterance(text="my studio has never been cleaner", uid="u1"),
        utterance(text="my studio has never been cleaner again", uid="u2"),
    )
    for u in (old, new):
        ledger.append_utterance(conn, u)
    b = belief(bid="b1", utterance_id="u1")
    beliefs.insert_belief(conn, b)
    assert beliefs.last_support(conn, REL) == {b.id: old.at}
    beliefs.add_evidence(
        conn, b.id, Evidence(UtteranceId("u2"), "my studio has never been cleaner")
    )
    assert beliefs.last_support(conn, REL) == {b.id: new.at}


def test_added_evidence_is_still_checked_by_the_database(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.types import Evidence, UtteranceId  # noqa: PLC0415
    from companion.store.sqlite import beliefs  # noqa: PLC0415

    ledger.append_utterance(conn, utterance(text="my studio has never been cleaner", uid="u1"))
    ledger.append_utterance(conn, utterance(text="something else entirely", uid="u2"))
    b = belief(bid="b1", utterance_id="u1")
    beliefs.insert_belief(conn, b)
    with pytest.raises(sqlite3.DatabaseError):
        beliefs.add_evidence(conn, b.id, Evidence(UtteranceId("u2"), "not in that message"))


def test_a_withdrawn_flag_leaves_the_list_but_stays_in_the_ledger(conn: sqlite3.Connection) -> None:
    t = _turn(conn, "t1")
    flags.add_flag(conn, Flag(FlagId("f1"), REL, t, FlagKind.OFF, "meant as a fav", T0))
    flags.withdraw_flag(conn, FlagId("f1"), "moved to a favourite", T0)
    assert flags.list_flags(conn, REL) == []
    assert conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0] == 1
