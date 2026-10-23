"""Prefixes and the per-turn request record that make a turn replayable."""

from __future__ import annotations

import sqlite3

from companion.core.prompt.prefix import Prefix
from companion.core.replay import TurnRecord
from companion.core.types import RelationshipId, SessionId, TurnId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


def save_prefix(conn: sqlite3.Connection, p: Prefix) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT OR IGNORE INTO prefixes (sha256, system, tools_json, estimated_tokens)"
            " VALUES (?, ?, ?, ?)",
            (p.sha256, p.system, p.tools_json, p.estimated_tokens),
        )


def load_prefix(conn: sqlite3.Connection, sha256: str) -> Prefix | None:
    row = conn.execute("SELECT * FROM prefixes WHERE sha256 = ?", (sha256,)).fetchone()
    if row is None:
        return None
    return Prefix(
        system=str(row["system"]),
        tools_json=str(row["tools_json"]),
        sha256=str(row["sha256"]),
        estimated_tokens=int(row["estimated_tokens"]),
    )


def record_turn(conn: sqlite3.Connection, r: TurnRecord) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO turn_requests (turn_id, relationship_id, session_id, prefix_sha256,"
            " volatile, request_sha256, model, at, card) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.turn_id,
                r.relationship_id,
                r.session_id,
                r.prefix_sha256,
                r.volatile,
                r.request_sha256,
                r.model,
                iso(r.at),
                r.card,
            ),
        )


def get_turn(conn: sqlite3.Connection, turn_id: TurnId) -> TurnRecord | None:
    row = conn.execute("SELECT * FROM turn_requests WHERE turn_id = ?", (turn_id,)).fetchone()
    if row is None:
        return None
    model = row["model"]
    return TurnRecord(
        turn_id=TurnId(str(row["turn_id"])),
        relationship_id=RelationshipId(str(row["relationship_id"])),
        session_id=SessionId(str(row["session_id"])),
        prefix_sha256=str(row["prefix_sha256"]),
        volatile=str(row["volatile"]),
        request_sha256=str(row["request_sha256"]),
        model=str(model) if model is not None else None,
        at=parse_iso(str(row["at"])),
        card=str(row["card"]),
    )


def latest_turn(conn: sqlite3.Connection, relationship_id: RelationshipId) -> TurnId | None:
    row = conn.execute(
        "SELECT turn_id FROM turn_requests WHERE relationship_id = ? ORDER BY at DESC, rowid DESC"
        " LIMIT 1",
        (relationship_id,),
    ).fetchone()
    return TurnId(str(row["turn_id"])) if row is not None else None
