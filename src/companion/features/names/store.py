"""Things named in memory (fetch on mention, shadow). Append-only."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.features.names.logic import Row
from companion.lib.sqlite.db import iso, write_tx


def add(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    rows: Sequence[Row],
    read: Iterable[BeliefId],
    *,
    model: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO belief_names (relationship_id, belief_id, name, terms, model, prompt, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (rel, r.belief_id, r.name, json.dumps(list(r.terms)), model, prompt, iso(at))
                for r in rows
            ],
        )
        conn.executemany(
            "INSERT INTO name_reads (relationship_id, belief_id, at) VALUES (?, ?, ?)",
            [(rel, bid, iso(at)) for bid in read],
        )


def rows(conn: sqlite3.Connection, rel: RelationshipId) -> list[Row]:
    found = conn.execute(
        "SELECT belief_id, name, terms FROM belief_names WHERE relationship_id = ? ORDER BY id",
        (rel,),
    ).fetchall()
    return [
        Row(BeliefId(str(r["belief_id"])), str(r["name"]), tuple(json.loads(str(r["terms"]))))
        for r in found
    ]


def read(conn: sqlite3.Connection, rel: RelationshipId) -> set[BeliefId]:
    found = conn.execute(
        "SELECT DISTINCT belief_id FROM name_reads WHERE relationship_id = ?", (rel,)
    ).fetchall()
    return {BeliefId(str(r["belief_id"])) for r in found}
