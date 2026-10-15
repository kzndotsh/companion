"""Failures the user marked."""

from __future__ import annotations

import sqlite3

from companion.core.types import Flag, FlagId, FlagKind, RelationshipId, TurnId
from companion.store.sqlite.db import iso, parse_iso, write_tx


def add_flag(conn: sqlite3.Connection, f: Flag) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO flags (id, relationship_id, turn_id, kind, note, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (f.id, f.relationship_id, f.turn_id, f.kind, f.note, iso(f.at)),
        )


def list_flags(conn: sqlite3.Connection, relationship_id: RelationshipId) -> list[Flag]:
    rows = conn.execute(
        "SELECT * FROM flags WHERE relationship_id = ? ORDER BY at, id", (relationship_id,)
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
