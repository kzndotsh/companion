"""The calendar's queries: when they first wrote, and what it offered."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from companion.core.types import Json, RelationshipId
from companion.features.calendar.logic import OFFERED
from companion.lib.sqlite.db import iso, parse_iso


def first_message(conn: sqlite3.Connection, rel: RelationshipId) -> datetime | None:
    """When their first message in the ledger was sent, or None before they have written."""
    row = conn.execute(
        "SELECT MIN(at) AS at FROM utterances WHERE relationship_id = ? AND speaker = 'user'",
        (rel,),
    ).fetchone()
    return parse_iso(str(row["at"])) if row is not None and row["at"] is not None else None


def offered_since(
    conn: sqlite3.Connection, rel: RelationshipId, since: datetime
) -> list[tuple[datetime, dict[str, Json]]]:
    """Every occasion offered at or after a time, oldest first, with its logged detail."""
    rows = conn.execute(
        "SELECT at, detail FROM decisions WHERE relationship_id = ? AND key = ? AND at >= ?"
        " ORDER BY at, id",
        (rel, OFFERED, iso(since)),
    ).fetchall()
    out: list[tuple[datetime, dict[str, Json]]] = []
    for r in rows:
        loaded: Json = json.loads(str(r["detail"])) if r["detail"] is not None else None
        out.append((parse_iso(str(r["at"])), loaded if isinstance(loaded, dict) else {}))
    return out
