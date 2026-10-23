"""Failures the user marked."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.types import Flag, FlagId, FlagKind, RelationshipId, TurnId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


def add_flag(conn: sqlite3.Connection, f: Flag) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO flags (id, relationship_id, turn_id, kind, note, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (f.id, f.relationship_id, f.turn_id, f.kind, f.note, iso(f.at)),
        )


def withdraw_flag(conn: sqlite3.Connection, flag_id: FlagId, reason: str, at: datetime) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO flag_withdrawals (flag_id, reason, at) VALUES (?, ?, ?)",
            (flag_id, reason, iso(at)),
        )


def list_flags(conn: sqlite3.Connection, relationship_id: RelationshipId) -> list[Flag]:
    rows = conn.execute(
        "SELECT * FROM flags f WHERE relationship_id = ?"
        " AND NOT EXISTS (SELECT 1 FROM flag_withdrawals w WHERE w.flag_id = f.id) ORDER BY at, id",
        (relationship_id,),
    ).fetchall()
    return [
        Flag(
            id=FlagId(str(r["id"])),
            relationship_id=RelationshipId(str(r["relationship_id"])),
            turn_id=TurnId(str(r["turn_id"])),
            kind=FlagKind(str(r["kind"])),
            note=str(r["note"]),
            at=parse_iso(str(r["at"])),
        )
        for r in rows
    ]
