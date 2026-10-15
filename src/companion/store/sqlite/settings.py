"""Settings and view checks. Both are append-only logs; the newest row is the current answer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from companion.core.types import BeliefId, Json, RelationshipId
from companion.store.sqlite.db import iso, write_tx


def set_value(
    conn: sqlite3.Connection, rel: RelationshipId, key: str, value: str, at: datetime
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO settings_log (relationship_id, key, value, at) VALUES (?, ?, ?, ?)",
            (rel, key, value, iso(at)),
        )


def get_value(conn: sqlite3.Connection, rel: RelationshipId, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM settings_log WHERE relationship_id = ? AND key = ?"
        " ORDER BY id DESC LIMIT 1",
        (rel, key),
    ).fetchone()
    return str(row["value"]) if row is not None else None


def record_check(
    conn: sqlite3.Connection,
    belief_id: BeliefId,
    *,
    conflicts: bool,
    detail: dict[str, Json],
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO view_checks (belief_id, conflicts, detail, at) VALUES (?, ?, ?, ?)",
            (belief_id, int(conflicts), json.dumps(detail), iso(at)),
        )


def latest_checks(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, bool]:
    """For each belief, whether its newest check found a conflict. Unchecked beliefs are absent."""
    rows = conn.execute(
        "SELECT c.belief_id AS id, c.conflicts AS conflicts FROM view_checks c"
        " JOIN beliefs b ON b.id = c.belief_id"
        " WHERE b.relationship_id = ? AND c.id = ("
        "   SELECT MAX(id) FROM view_checks WHERE belief_id = c.belief_id)",
        (rel,),
    ).fetchall()
    return {BeliefId(str(r["id"])): bool(r["conflicts"]) for r in rows}
