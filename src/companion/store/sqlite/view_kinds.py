"""The kind of each of the companion's views, read only (the lore feature writes them; the newest
label wins)."""

from __future__ import annotations

import sqlite3

from companion.core.types import BeliefId, RelationshipId
from companion.core.views import ViewKind


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, ViewKind]:
    rows = conn.execute(
        "SELECT belief_id, kind FROM view_kinds WHERE relationship_id = ? ORDER BY id", (rel,)
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): ViewKind(str(r["kind"])) for r in rows}
