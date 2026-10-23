"""Memory labels, append-only (J48). The newest label for a memory wins."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.features.knowing.logic import Depth, Domain, Label
from companion.lib.sqlite.db import iso, write_tx


def add(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    labels: Sequence[Label],
    *,
    model: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO belief_labels"
            " (relationship_id, belief_id, domain, depth, model, prompt, at)"
            " VALUES (?,?,?,?,?,?,?)",
            [
                (rel, x.belief_id, x.domain.value, x.depth.value, model, prompt, iso(at))
                for x in labels
            ],
        )


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, Label]:
    """The newest label of each memory. A row with a value this code no longer knows is skipped."""
    rows = conn.execute(
        "SELECT belief_id, domain, depth FROM belief_labels WHERE relationship_id = ? ORDER BY id",
        (rel,),
    ).fetchall()
    domains, depths = {d.value for d in Domain}, {d.value for d in Depth}
    out: dict[BeliefId, Label] = {}
    for r in rows:
        if r["domain"] in domains and r["depth"] in depths:
            bid = BeliefId(str(r["belief_id"]))
            out[bid] = Label(bid, Domain(str(r["domain"])), Depth(str(r["depth"])))
    return out
