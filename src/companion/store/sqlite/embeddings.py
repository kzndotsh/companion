"""Memory embeddings, append-only. Stored as float32, read back as unit vectors."""

from __future__ import annotations

import sqlite3
from array import array
from collections.abc import Mapping
from datetime import datetime

from companion.core.relevance import Vector
from companion.core.types import BeliefId, RelationshipId
from companion.store.sqlite.db import iso, write_tx


def add(
    conn: sqlite3.Connection,
    rel: RelationshipId,
    vectors: Mapping[BeliefId, Vector],
    *,
    model: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO belief_embeddings (relationship_id, belief_id, model, vector, at)"
            " VALUES (?,?,?,?,?)",
            [(rel, bid, model, array("f", v).tobytes(), iso(at)) for bid, v in vectors.items()],
        )


def latest(conn: sqlite3.Connection, rel: RelationshipId, model: str) -> dict[BeliefId, Vector]:
    rows = conn.execute(
        "SELECT belief_id, vector FROM belief_embeddings WHERE relationship_id = ? AND model = ?"
        " ORDER BY id",
        (rel, model),
    ).fetchall()
    out: dict[BeliefId, Vector] = {}
    for r in rows:
        floats = array("f")
        floats.frombytes(bytes(r["vector"]))
        out[BeliefId(str(r["belief_id"]))] = tuple(floats)
    return out
