from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

import pytest

from companion.core.openloops import LoopState, OpenLoop
from companion.core.types import Utterance, UtteranceId
from companion.store.sqlite import ledger, open_loops
from companion.store.sqlite.open_loops import ReachOut
from tests.conftest import REL, T0


def _loop(conn: sqlite3.Connection, utterance: Callable[..., Utterance]) -> OpenLoop:
    u = utterance(text="going to the vet tomorrow", uid="u-src")
    ledger.append_utterance(conn, u)
    loop = OpenLoop(
        "l1",
        REL,
        "vet visit",
        "going to the vet tomorrow",
        UtteranceId("u-src"),
        T0 + timedelta(days=1),
        0,
        T0,
    )
    open_loops.add_loop(conn, loop)
    return loop


def test_a_new_loop_is_open_and_reads_back_whole(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    loop = _loop(conn, utterance)
    assert open_loops.loops(conn, REL) == [loop]


def test_its_state_is_its_newest_event(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _loop(conn, utterance)
    open_loops.add_event(conn, "l1", LoopState.ASKED, "shadow reach-out", T0)
    assert open_loops.loops(conn, REL)[0].state is LoopState.ASKED
    open_loops.add_event(conn, "l1", LoopState.RESOLVED, "they said how it went", T0)
    assert open_loops.loops(conn, REL)[0].state is LoopState.RESOLVED


def test_the_three_tables_are_append_only(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _loop(conn, utterance)
    open_loops.add_reach_out(
        conn, ReachOut("r1", REL, "l1", "shadow", "how did the vet go?", "due", T0)
    )
    for sql in (
        "UPDATE open_loops SET claim = 'x'",
        "DELETE FROM open_loops",
        "UPDATE open_loop_events SET state = 'open'",
        "DELETE FROM open_loop_events",
        "UPDATE reach_outs SET draft = 'x'",
        "DELETE FROM reach_outs",
    ):
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql)


def test_reach_outs_can_be_listed_since_a_time(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _loop(conn, utterance)
    old = ReachOut("r1", REL, "l1", "shadow", "old", "why", T0)
    new = ReachOut("r2", REL, "l1", "shadow", "new", "why", T0 + timedelta(days=2))
    open_loops.add_reach_out(conn, old)
    open_loops.add_reach_out(conn, new)
    assert [r.id for r in open_loops.reach_outs_since(conn, REL)] == ["r1", "r2"]
    assert [r.id for r in open_loops.reach_outs_since(conn, REL, T0 + timedelta(days=1))] == ["r2"]


def test_a_loop_must_point_at_a_real_message(conn: sqlite3.Connection) -> None:
    ghost = OpenLoop("l9", REL, "x", "x", UtteranceId("nope"), T0, 0, T0)
    with pytest.raises(sqlite3.IntegrityError):
        open_loops.add_loop(conn, ghost)


def test_note_only_reads_back_and_events_are_counted_by_reason(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    base = _loop(conn, utterance)
    open_loops.add_loop(conn, replace(base, id="l2", note_only=True))
    assert [lp.note_only for lp in open_loops.loops(conn, REL)] == [False, True]
    open_loops.add_event(conn, "l2", LoopState.ASKED, "offered", T0)
    open_loops.add_event(conn, "l2", LoopState.ASKED, "offered", T0)
    open_loops.add_event(conn, "l1", LoopState.ASKED, "shadow reach-out", T0)
    assert open_loops.events_with_reason(conn, REL, "offered") == {"l2": 2}
