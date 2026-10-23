"""Turns the user loved."""

from __future__ import annotations

import sqlite3

from companion.core.types import Favorite, FavoriteId, RelationshipId, TurnId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


def add_favorite(conn: sqlite3.Connection, f: Favorite) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO favorites (id, relationship_id, turn_id, note, at) VALUES (?, ?, ?, ?, ?)",
            (f.id, f.relationship_id, f.turn_id, f.note, iso(f.at)),
        )


def list_favorites(conn: sqlite3.Connection, relationship_id: RelationshipId) -> list[Favorite]:
    rows = conn.execute(
        "SELECT * FROM favorites WHERE relationship_id = ? ORDER BY at, id", (relationship_id,)
    ).fetchall()
    return [
        Favorite(
            id=FavoriteId(str(r["id"])),
            relationship_id=RelationshipId(str(r["relationship_id"])),
            turn_id=TurnId(str(r["turn_id"])),
            note=str(r["note"]),
            at=parse_iso(str(r["at"])),
        )
        for r in rows
    ]
