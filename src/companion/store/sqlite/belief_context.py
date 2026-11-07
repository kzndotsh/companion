"""What they were talking about when each memory was said, in one place: the columns of
`belief_context` are named here. The upkeep context step writes through `insert`; the newest line
of each memory wins (`latest`)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class ContextRow:
    """One line as stored: the memory, what they were talking about, and the prompt's
    `name@version` and when it was read."""

    belief_id: BeliefId
    context: str
    prompt: str
    at: datetime


def insert(conn: sqlite3.Connection, rel: RelationshipId, row: ContextRow) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO belief_context (relationship_id, belief_id, context, prompt, at)"
            " VALUES (?,?,?,?,?)",
            (rel, row.belief_id, row.context, row.prompt, iso(row.at)),
        )


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, str]:
    rows = conn.execute(
        "SELECT belief_id, context FROM belief_context WHERE relationship_id = ? ORDER BY id",
        (rel,),
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): str(r["context"]) for r in rows}
