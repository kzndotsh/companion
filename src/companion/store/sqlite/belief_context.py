"""What they were talking about when each memory was said, read only (the upkeep context step writes
them; the newest line of each memory wins)."""

from __future__ import annotations

import sqlite3

from companion.core.types import BeliefId, RelationshipId


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, str]:
    rows = conn.execute(
        "SELECT belief_id, context FROM belief_context WHERE relationship_id = ? ORDER BY id",
        (rel,),
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): str(r["context"]) for r in rows}
