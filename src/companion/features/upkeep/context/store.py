"""What they were talking about when each memory was said (J51). Append-only."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.lib.sqlite.db import iso, write_tx


def add(  # noqa: PLR0913, PLR0917
    conn: sqlite3.Connection,
    rel: RelationshipId,
    belief_id: BeliefId,
    context: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO belief_context (relationship_id, belief_id, context, prompt, at)"
            " VALUES (?,?,?,?,?)",
            (rel, belief_id, context, prompt, iso(at)),
        )


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, str]:
    rows = conn.execute(
        "SELECT belief_id, context FROM belief_context WHERE relationship_id = ? ORDER BY id",
        (rel,),
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): str(r["context"]) for r in rows}
