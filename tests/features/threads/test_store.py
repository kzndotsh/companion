from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

import pytest

from companion.core.reachout import Fate, ReachOut
from companion.core.types import Sensitivity, Utterance, UtteranceId
from companion.features.threads.logic import Source, Thread, ThreadState
from companion.features.threads.store import Threads
from companion.store.sqlite import ledger, reach_outs
from tests.conftest import REL, T0


def _loop(conn: sqlite3.Connection, utterance: Callable[..., Utterance]) -> Thread:
    u = utterance(text="going to the vet tomorrow", uid="u-src")
    ledger.append_utterance(conn, u)
    loop = Thread(
        "l1",
        REL,
        "vet visit",
        "going to the vet tomorrow",
        UtteranceId("u-src"),
        T0 + timedelta(days=1),
        Sensitivity.ORDINARY,
        T0,
    )
    Threads(conn).add_loop(loop)
    return loop


def test_a_new_loop_is_open_and_reads_back_whole(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    loop = _loop(conn, utterance)
    assert Threads(conn).loops(REL) == [loop]


def test_a_row_from_before_sources_reads_as_a_plan(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    ledger.append_utterance(conn, utterance(text="exam on friday", uid="u-old"))
    conn.execute(
        "INSERT INTO open_loops (id, relationship_id, claim, quote, source_utterance_id,"
        " follow_up_at, sensitivity, created_at) VALUES ('old', ?, 'exam', 'exam on friday',"
        " 'u-old', ?, 0, ?)",
        (REL, (T0 + timedelta(days=2)).isoformat(), T0.isoformat()),
    )
    conn.execute(
        "INSERT INTO open_loop_events (loop_id, state, reason, at) VALUES ('old', 'open', 'x', ?)",
        (T0.isoformat(),),
    )
    assert Threads(conn).loops(REL)[0].source is Source.PLAN


def test_its_state_is_its_newest_event(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _loop(conn, utterance)
    Threads(conn).add_event("l1", ThreadState.ASKED, "shadow reach-out", T0)
    assert Threads(conn).loops(REL)[0].state is ThreadState.ASKED
    Threads(conn).add_event("l1", ThreadState.RESOLVED, "they said how it went", T0)
    assert Threads(conn).loops(REL)[0].state is ThreadState.RESOLVED


def test_the_three_tables_are_append_only(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _loop(conn, utterance)
    reach_outs.add(conn, ReachOut("r1", REL, "l1", Fate.SHADOW, "how did the vet go?", "due", T0))
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
    old = ReachOut("r1", REL, "l1", Fate.SHADOW, "old", "why", T0)
    new = ReachOut("r2", REL, "l1", Fate.SHADOW, "new", "why", T0 + timedelta(days=2))
    reach_outs.add(conn, old)
    reach_outs.add(conn, new)
    assert [r.id for r in reach_outs.since(conn, REL)] == ["r1", "r2"]
    assert [r.id for r in reach_outs.since(conn, REL, T0 + timedelta(days=1))] == ["r2"]


def test_a_loop_must_point_at_a_real_message(conn: sqlite3.Connection) -> None:
    ghost = Thread("l9", REL, "x", "x", UtteranceId("nope"), T0, Sensitivity.ORDINARY, T0)
    with pytest.raises(sqlite3.IntegrityError):
        Threads(conn).add_loop(ghost)


def test_note_only_reads_back_and_events_are_counted_by_key(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    base = _loop(conn, utterance)
    Threads(conn).add_loop(replace(base, id="l2", note_only=True))
    assert [lp.note_only for lp in Threads(conn).loops(REL)] == [False, True]
    Threads(conn).add_event("l2", ThreadState.ASKED, "offered", T0, key="offered")
    Threads(conn).add_event("l2", ThreadState.ASKED, "offered", T0)  # from before keys
    Threads(conn).add_event("l2", ThreadState.ASKED, "other words", T0, key="something else")
    Threads(conn).add_event("l1", ThreadState.ASKED, "shadow reach-out", T0)
    assert Threads(conn).events_with_key(REL, "offered") == {"l2": 2}
