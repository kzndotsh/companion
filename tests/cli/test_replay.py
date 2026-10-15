from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from tests.conftest import REL, T0

from companion.cli import replay as cli_replay
from companion.cli.main import main
from companion.core.prompt.prefix import Prefix, build_prefix
from companion.core.prompt.request import Message, build_request, request_sha256
from companion.core.replay import ReplayError, TurnRecord
from companion.core.types import (
    Decision,
    DecisionId,
    DecisionKind,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
)
from companion.store.sqlite import decisions, ledger, turns
from companion.store.sqlite import replay as store_replay
from companion.store.sqlite.db import connect, migrate

PERSONA = "You are a companion with a settled voice. " * 200


def _prefix() -> Prefix:
    return build_prefix(PERSONA)


def _seed(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> tuple[TurnRecord, Prefix]:
    p = _prefix()
    turns.save_prefix(conn, p)
    first = utterance(text="morning", uid="u1")
    reply = utterance(text="hey, you're up early", speaker=Speaker.COMPANION, uid="u2")
    second = utterance(text="couldn't sleep", uid="u3")
    for u in (first, reply, second):
        ledger.append_utterance(conn, u)
    request = build_request(
        p,
        [Message("user", "morning"), Message("assistant", reply.text)],
        second.text,
        "it is 06:10",
    )
    record = TurnRecord(
        turn_id=second.turn_id,
        relationship_id=REL,
        session_id=SessionId("s1"),
        prefix_sha256=p.sha256,
        volatile="it is 06:10",
        request_sha256=request_sha256(request),
        model="test-model",
        at=T0,
    )
    turns.record_turn(conn, record)
    return record, p


def test_replay_rebuilds_a_matching_request(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    record, _ = _seed(conn, utterance)
    report = store_replay.replay(conn, record.turn_id)
    assert report.matched
    assert [m.role for m in report.request.messages][-1] == "user"
    assert "it is 06:10" in report.request.messages[-1].content


def test_later_turns_do_not_change_the_replay(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    record, _ = _seed(conn, utterance)
    ledger.append_utterance(conn, utterance(text="anyway, bye", uid="u9"))
    assert store_replay.replay(conn, record.turn_id).matched


def test_wrong_recorded_hash_reports_mismatch(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    record, _ = _seed(conn, utterance)
    late = utterance(text="couldn't sleep", uid="u7")
    ledger.append_utterance(conn, late)
    forged = replace(record, turn_id=late.turn_id, request_sha256="0" * 64)
    turns.record_turn(conn, forged)
    assert not store_replay.replay(conn, forged.turn_id).matched


def test_unknown_turn_is_an_error(conn: sqlite3.Connection) -> None:
    with pytest.raises(ReplayError):
        store_replay.replay(conn, TurnId("nope"))


def test_turn_records_cannot_be_edited(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    record, _ = _seed(conn, utterance)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE turn_requests SET volatile = 'x' WHERE turn_id = ?", (record.turn_id,))


def test_decisions_are_shown(conn: sqlite3.Connection, utterance: Callable[..., Utterance]) -> None:
    record, _ = _seed(conn, utterance)
    decisions.append_decision(
        conn,
        Decision(
            id=DecisionId("d1"),
            relationship_id=REL,
            session_id=SessionId("s1"),
            turn_id=record.turn_id,
            trace_id=TraceId("tr1"),
            kind=DecisionKind.DO_NOTHING,
            reason="nothing worth surfacing",
            at=T0,
        ),
    )
    out = cli_replay.render(store_replay.replay(conn, record.turn_id))
    assert "MATCH" in out
    assert "nothing worth surfacing" in out


def test_cli_exit_codes(tmp_path: Path, utterance: Callable[..., Utterance]) -> None:
    db = tmp_path / "r.sqlite"
    c = connect(db)
    migrate(c)
    record, _ = _seed(c, utterance)
    c.close()
    assert main(["replay", record.turn_id, "--db", str(db)]) == 0
    assert main(["replay", "missing", "--db", str(db)]) == 2
