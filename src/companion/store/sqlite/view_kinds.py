"""The kind of each of the companion's views (ADR 0020). Append-only; the newest label wins."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.features.lore.logic import Kind, Labelled
from companion.lib.sqlite.db import iso, write_tx


def add(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    labels: Sequence[Labelled],
    *,
    model: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO view_kinds (relationship_id, belief_id, kind, model, prompt, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(rel, x.belief_id, x.kind, model, prompt, iso(at)) for x in labels],
        )


def kinds(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, Kind]:
    rows = conn.execute(
        "SELECT belief_id, kind FROM view_kinds WHERE relationship_id = ? ORDER BY id", (rel,)
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): Kind(str(r["kind"])) for r in rows}
