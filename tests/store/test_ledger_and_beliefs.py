from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.types import (
    Belief,
    BeliefId,
    Evidence,
    Frame,
    Speaker,
    Subject,
    Utterance,
    UtteranceId,
)
from companion.lib.sqlite.db import connect, iso
from companion.store.sqlite import beliefs, ledger
from companion.store.sqlite.db import migrate
from tests.conftest import REL, T0


def seed(conn: sqlite3.Connection, u: Utterance, b: Belief | None = None) -> None:
    ledger.append_utterance(conn, u)
    if b is not None:
        beliefs.insert_belief(conn, b)


def test_migrate_is_idempotent(conn: sqlite3.Connection) -> None:
    assert migrate(conn) == []


def test_wal_and_foreign_keys_are_on(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_utterance_round_trips(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    u = utterance()
    ledger.append_utterance(conn, u)
    assert ledger.get_utterance(conn, u.id) == u


def test_ledger_is_append_only(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    u = utterance()
    ledger.append_utterance(conn, u)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE utterances SET text = 'edited' WHERE id = ?", (u.id,))
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM utterances WHERE id = ?", (u.id,))


def test_belief_round_trips_with_evidence(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    u, b = utterance(uid="u1"), belief()
    seed(conn, u, b)
    assert beliefs.get_belief(conn, b.id) == b


def test_quote_not_in_the_source_is_refused_by_the_store(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    ledger.append_utterance(conn, utterance(uid="u1"))
    bad = belief(evidence=(Evidence(UtteranceId("u1"), "she drives past her old office"),))
    with pytest.raises(sqlite3.DatabaseError, match=r"verbatim|occur"):
        beliefs.insert_belief(conn, bad)
    assert beliefs.get_belief(conn, bad.id) is None, "failed insert must roll back the belief too"


def test_evidence_must_come_from_the_beliefs_own_speaker(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    ledger.append_utterance(
        conn, utterance("you mentioned the grant", speaker=Speaker.COMPANION, uid="u1")
    )
    b = belief(quote="the grant")
    with pytest.raises(sqlite3.DatabaseError, match="speaker"):
        beliefs.insert_belief(conn, b)


def test_evidence_frame_must_match_the_belief_frame(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    ledger.append_utterance(conn, utterance("I'm a dragon", frame=Frame.PLAY, uid="u1"))
    with pytest.raises(sqlite3.DatabaseError, match="frame"):
        beliefs.insert_belief(conn, belief(quote="a dragon"))


def test_beliefs_are_never_deleted(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    b = belief()
    seed(conn, utterance(uid="u1"), b)
    with pytest.raises(sqlite3.DatabaseError, match="never deleted"):
        conn.execute("DELETE FROM beliefs WHERE id = ?", (b.id,))


def test_a_beliefs_claim_never_changes(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    b = belief()
    seed(conn, utterance(uid="u1"), b)
    with pytest.raises(sqlite3.DatabaseError, match="supersede"):
        conn.execute("UPDATE beliefs SET claim = 'something else' WHERE id = ?", (b.id,))


def test_the_schema_repeats_the_python_invariants(conn: sqlite3.Connection) -> None:
    """A raw writer that skips the dataclasses still cannot record a companion-said user fact."""
    conn.execute(
        "INSERT INTO utterances VALUES ('u9', 'r', 's', 't', 'companion', 'x y z', 'real', 'c', ?)",
        (iso(T0),),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO beliefs (id, relationship_id, subject, kind, claim, provenance, speaker,"
            " frame, confidence, valid_from, recorded_at) VALUES"
            " ('bx', 'r', 'user', 'trait', 'c', 'stated', 'companion', 'real', 0.5, ?, ?)",
            (iso(T0), iso(T0)),
        )


def test_supersession_closes_the_old_belief_and_keeps_both(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    old = belief("b1", "u1", "my studio has never been cleaner")
    u2 = utterance("the studio is a mess, honestly a good sign", uid="u2")
    new = belief(
        "b2",
        "u2",
        "the studio is a mess",
        claim="A messy studio means she is absorbed and doing well",
        valid_from=T0 + timedelta(days=21),
    )
    seed(conn, utterance(uid="u1"), old)
    ledger.append_utterance(conn, u2)
    beliefs.supersede(conn, old.id, new, at=T0 + timedelta(days=21))

    closed = beliefs.get_belief(conn, BeliefId("b1"))
    assert closed is not None
    assert closed.superseded_by == BeliefId("b2")
    assert closed.valid_until == T0 + timedelta(days=21)
    assert [b.id for b in beliefs.current_beliefs(conn, REL, Subject.USER)] == [BeliefId("b2")]


def test_a_closed_belief_cannot_be_reopened(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    old = belief("b1", "u1")
    new = belief("b2", "u2", "the studio is a mess")
    seed(conn, utterance(uid="u1"), old)
    ledger.append_utterance(conn, utterance("the studio is a mess", uid="u2"))
    beliefs.supersede(conn, old.id, new, at=T0 + timedelta(days=1))
    with pytest.raises(sqlite3.DatabaseError, match="reopened"):
        conn.execute("UPDATE beliefs SET valid_until = NULL, superseded_by = NULL WHERE id = 'b1'")


def test_supersession_is_atomic(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    old = belief("b1", "u1")
    seed(conn, utterance(uid="u1"), old)
    bad_new = belief("b2", "u1", "never said this")
    with pytest.raises(sqlite3.DatabaseError):
        beliefs.supersede(conn, old.id, bad_new, at=T0 + timedelta(days=1))
    still = beliefs.get_belief(conn, old.id)
    assert still is not None
    assert still.is_current


def test_a_second_connection_waits_for_the_writer_lock(tmp_path: Path) -> None:
    path = tmp_path / "w.sqlite"
    a = connect(path)
    migrate(a)
    b = connect(path)
    b.execute("PRAGMA busy_timeout = 50")
    a.execute("BEGIN IMMEDIATE")
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        b.execute("BEGIN IMMEDIATE")
    a.execute("ROLLBACK")
    b.execute("BEGIN IMMEDIATE")
    b.execute("ROLLBACK")


def test_every_belief_has_evidence_audit(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    seed(conn, utterance(uid="u1"), belief())
    assert beliefs.beliefs_without_evidence(conn) == []
    conn.execute(
        "INSERT INTO beliefs (id, relationship_id, subject, kind, claim, provenance, speaker,"
        " frame, confidence, valid_from, recorded_at) VALUES"
        " ('orphan', 'rel-1', 'user', 'trait', 'c', 'stated', 'user', 'real', 0.5, ?, ?)",
        (iso(T0), iso(T0)),
    )
    assert beliefs.beliefs_without_evidence(conn) == [BeliefId("orphan")]
