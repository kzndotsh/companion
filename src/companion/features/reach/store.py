"""Its own reach-outs (ADR 0021): would-sends in shadow, sends when live, and dropped drafts.
Append-only (`store/sqlite/migrations/0032_own_reach_outs.sql`)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import Json, RelationshipId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Own:
    id: str
    relationship_id: RelationshipId
    kind: str
    thing: str  # the one thing it is about, its id and text, or empty
    draft: str
    mode: str  # "shadow" (would send), "live" (sent) or "dropped" (failed the check)
    detail: dict[str, Json]  # the rhythm, the share, the dial and why
    at: datetime


def add(conn: sqlite3.Connection, r: Own) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO own_reach_outs (id, relationship_id, kind, thing, draft, mode, detail, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.id,
                r.relationship_id,
                r.kind,
                r.thing,
                r.draft,
                r.mode,
                json.dumps(r.detail, sort_keys=True),
                iso(r.at),
            ),
        )


def since(conn: sqlite3.Connection, rel: RelationshipId, start: datetime | None) -> list[Own]:
    rows = conn.execute(
        "SELECT * FROM own_reach_outs WHERE relationship_id = ? AND at >= ? ORDER BY at, id",
        (rel, iso(start) if start else ""),
    ).fetchall()
    out: list[Own] = []
    for r in rows:
        loaded: Json = json.loads(str(r["detail"]))
        out.append(
            Own(
                str(r["id"]),
                RelationshipId(str(r["relationship_id"])),
                str(r["kind"]),
                str(r["thing"]),
                str(r["draft"]),
                str(r["mode"]),
                loaded if isinstance(loaded, dict) else {},
                parse_iso(str(r["at"])),
            )
        )
    return out
