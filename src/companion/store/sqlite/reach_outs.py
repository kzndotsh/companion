"""The reach-outs about a plan (`reach_outs`). Append-only. Core storage because every kind of
reach-out is read together: threads writes these, the reach feature and `companion initiative` read
them beside the others (ADR 0023)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.reachout import Fate, ReachOut
from companion.core.types import RelationshipId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


def add(conn: sqlite3.Connection, r: ReachOut) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO reach_outs (id, relationship_id, loop_id, mode, draft, reason, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r.id, r.relationship_id, r.loop_id, r.fate.value, r.draft, r.reason, iso(r.at)),
        )


def since(
    conn: sqlite3.Connection, rel: RelationshipId, start: datetime | None = None
) -> list[ReachOut]:
    rows = conn.execute(
        "SELECT * FROM reach_outs WHERE relationship_id = ? AND at >= ? ORDER BY at, id",
        (rel, iso(start) if start else ""),
    ).fetchall()
    return [
        ReachOut(
            str(r["id"]),
            RelationshipId(str(r["relationship_id"])),
            str(r["loop_id"]),
            Fate(str(r["mode"])),
            str(r["draft"]),
            str(r["reason"]),
            parse_iso(str(r["at"])),
        )
        for r in rows
    ]
