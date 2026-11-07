"""A bookmark: how far a reader has read the conversation, kept as an append-only table whose newest
row is the place (`upto_at`, `upto_id`). Two readers keep a plain one (`PlainTable`); the others
have a bookmark inside a richer table and read the place from their own row with `place_of`."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Literal

from companion.core.types import RelationshipId, UtteranceId
from companion.lib.sqlite.db import iso, parse_iso, write_tx

type Place = tuple[datetime, UtteranceId]
type PlainTable = Literal["story_reads", "scene_reads"]

_NEWEST: dict[PlainTable, str] = {
    "story_reads": "SELECT upto_at, upto_id FROM story_reads WHERE relationship_id = ?"
    " ORDER BY id DESC LIMIT 1",
    "scene_reads": "SELECT upto_at, upto_id FROM scene_reads WHERE relationship_id = ?"
    " ORDER BY id DESC LIMIT 1",
}
_MARK: dict[PlainTable, str] = {
    "story_reads": "INSERT INTO story_reads (relationship_id, upto_at, upto_id, at)"
    " VALUES (?,?,?,?)",
    "scene_reads": "INSERT INTO scene_reads (relationship_id, upto_at, upto_id, at)"
    " VALUES (?,?,?,?)",
}


def place_of(row: sqlite3.Row | None) -> Place | None:
    """The place a row of `upto_at`, `upto_id` holds, or None when there is no row."""
    if row is None:
        return None
    return parse_iso(str(row["upto_at"])), UtteranceId(str(row["upto_id"]))


def newest(conn: sqlite3.Connection, table: PlainTable, rel: RelationshipId) -> Place | None:
    return place_of(conn.execute(_NEWEST[table], (rel,)).fetchone())


def mark(
    conn: sqlite3.Connection, table: PlainTable, rel: RelationshipId, upto: Place, at: datetime
) -> None:
    with write_tx(conn):
        conn.execute(_MARK[table], (rel, iso(upto[0]), upto[1], iso(at)))
