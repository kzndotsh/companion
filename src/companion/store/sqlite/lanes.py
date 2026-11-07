"""The scene lane's placements, read only (the intimate feature writes them, `scene_lanes` is
append-only and the newest row is a memory's place)."""

from __future__ import annotations

import sqlite3

from companion.core.lane import Lane
from companion.core.types import BeliefId, RelationshipId


def intimate(conn: sqlite3.Connection, rel: RelationshipId) -> frozenset[BeliefId]:
    """The memories whose newest place is the intimate lane."""
    rows = conn.execute(
        "SELECT l.belief_id, l.lane FROM scene_lanes l JOIN beliefs b ON b.id = l.belief_id"
        " WHERE b.relationship_id = ? ORDER BY l.id",
        (rel,),
    ).fetchall()
    newest = {str(r["belief_id"]): str(r["lane"]) for r in rows}
    return frozenset(BeliefId(b) for b, lane in newest.items() if lane == Lane.INTIMATE.value)
