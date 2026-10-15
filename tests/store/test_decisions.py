from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    SessionId,
    TraceId,
    TurnId,
    Utterance,
)
from companion.store.sqlite import beliefs, decisions, ledger
from tests.conftest import REL, T0


def make(
    kind: DecisionKind,
    did: str = "d1",
    reason: str = "the user is mid-celebration; the cooldown has not elapsed",
    **overrides: object,
) -> Decision:
    fields: dict[str, object] = {
        "id": DecisionId(did),
        "relationship_id": REL,
        "session_id": SessionId("s1"),
        "turn_id": TurnId("t1"),
        "trace_id": TraceId("tr1"),
        "kind": kind,
        "reason": reason,
        "at": T0,
    }
    fields.update(overrides)
    return Decision(**fields)  # type: ignore[arg-type]


def test_silence_is_a_recordable_decision(conn: sqlite3.Connection) -> None:
    d = make(DecisionKind.DO_NOTHING, reason="quiet hours; patience table says wait")
    decisions.append_decision(conn, d)
    assert decisions.decisions_for_turn(conn, REL, TurnId("t1")) == [d]


def test_a_decision_without_a_reason_cannot_exist() -> None:
    with pytest.raises(ValueError, match="reason"):
        make(DecisionKind.DO_NOTHING, reason="  ")


def test_surface_and_withhold_must_name_a_belief() -> None:
    with pytest.raises(ValueError, match="name a belief"):
        make(DecisionKind.WITHHOLD)
    with pytest.raises(ValueError, match="name a belief"):
        make(DecisionKind.DO_NOTHING, belief_id=BeliefId("b1"))


def test_the_schema_enforces_the_same_rule(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (id, relationship_id, session_id, turn_id, trace_id, kind,"
            " belief_id, reason, at) VALUES ('x', 'r', 's', 't', 'tr', 'withhold', NULL, 'why', ?)",
            (T0.isoformat(),),
        )


def test_the_surfacing_history_of_a_belief_is_queryable(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    ledger.append_utterance(conn, utterance(uid="u1"))
    beliefs.insert_belief(conn, belief())
    b = BeliefId("b1")
    decisions.append_decision(
        conn, make(DecisionKind.WITHHOLD, "d1", "light moment; price too high", belief_id=b)
    )
    decisions.append_decision(
        conn,
        make(
            DecisionKind.SURFACE,
            "d2",
            "user invited it directly",
            belief_id=b,
            turn_id=TurnId("t2"),
            at=T0 + timedelta(days=2),
            detail={"price": 0.2, "utility": 0.7, "mention": "silent_use"},
        ),
    )
    history = decisions.decisions_for_belief(conn, b)
    assert [d.kind for d in history] == [DecisionKind.WITHHOLD, DecisionKind.SURFACE]
    assert history[1].detail == {"price": 0.2, "utility": 0.7, "mention": "silent_use"}


def test_decisions_are_append_only(conn: sqlite3.Connection) -> None:
    decisions.append_decision(conn, make(DecisionKind.DO_NOTHING))
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE decisions SET reason = 'edited'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM decisions")
