"""Load a recorded turn and rebuild its request from the ledger."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from companion.core.prompt.request import TalkerRequest
from companion.core.replay import ReplayError, TurnRecord, matches_record, rebuild_request
from companion.core.types import Decision, TurnId
from companion.store.sqlite import decisions, ledger, turns
from companion.store.sqlite.db import connect


@dataclass(frozen=True, slots=True)
class ReplayReport:
    record: TurnRecord
    request: TalkerRequest
    matched: bool
    decisions: list[Decision]


def replay(conn: sqlite3.Connection, turn_id: TurnId) -> ReplayReport:
    record = turns.get_turn(conn, turn_id)
    if record is None:
        msg = f"no recorded request for turn {turn_id}"
        raise ReplayError(msg)
    prefix = turns.load_prefix(conn, record.prefix_sha256)
    if prefix is None:
        msg = f"prefix {record.prefix_sha256[:12]} is missing from the store"
        raise ReplayError(msg)
    session = ledger.session_utterances(conn, record.relationship_id, record.session_id)
    request = rebuild_request(record, prefix, session)
    return ReplayReport(
        record=record,
        request=request,
        matched=matches_record(record, request),
        decisions=decisions.decisions_for_turn(conn, record.relationship_id, turn_id),
    )


def replay_file(db: Path, turn_id: str) -> ReplayReport:
    conn = connect(db)
    try:
        return replay(conn, TurnId(turn_id))
    finally:
        conn.close()
