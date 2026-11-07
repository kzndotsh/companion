"""The scene lane's placements, in one place: the columns of `scene_lanes` are named here, the
intimate feature writes rows through `insert` and reads its places through `newest`. The table is
append-only and the newest row is a memory's place."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.lane import Lane
from companion.core.types import BeliefId, RelationshipId
from companion.lib.sqlite.db import write_tx


@dataclass(frozen=True, slots=True)
class LaneRow:
    """One placement as stored: the lane, the stance when intimate, the reason when excluded, and
    who placed it (a model and the prompt's `name@version`) and when (ISO)."""

    belief_id: BeliefId
    lane: str
    stance: str | None
    why: str | None
    model: str
    prompt: str
    at: str


def insert(conn: sqlite3.Connection, rows: Sequence[LaneRow]) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO scene_lanes (belief_id, lane, stance, why, model, prompt, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r.belief_id, r.lane, r.stance, r.why, r.model, r.prompt, r.at) for r in rows],
        )


def newest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, LaneRow]:
    """Each labelled memory's newest placement."""
    rows = conn.execute(
        "SELECT l.* FROM scene_lanes l JOIN beliefs b ON b.id = l.belief_id"
        " WHERE b.relationship_id = ? ORDER BY l.id",
        (rel,),
    ).fetchall()
    return {
        BeliefId(str(r["belief_id"])): LaneRow(
            BeliefId(str(r["belief_id"])),
            str(r["lane"]),
            None if r["stance"] is None else str(r["stance"]),
            None if r["why"] is None else str(r["why"]),
            str(r["model"]),
            str(r["prompt"]),
            str(r["at"]),
        )
        for r in rows
    }


def intimate(conn: sqlite3.Connection, rel: RelationshipId) -> frozenset[BeliefId]:
    """The memories whose newest place is the intimate lane."""
    return frozenset(b for b, r in newest(conn, rel).items() if r.lane == Lane.INTIMATE.value)
