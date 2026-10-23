"""The times they spent together (J12). Append-only."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId, UtteranceId
from companion.store.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Episode:
    id: str
    first_id: UtteranceId
    last_id: UtteranceId
    start_at: datetime
    end_at: datetime
    messages: int
    kind: str
    scene_share: float
    top_severity: int
    firsts: tuple[str, ...]
    gist: str
    prompt: str
    at: datetime


def add(conn: sqlite3.Connection, rel: RelationshipId, e: Episode) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO episodes (id, relationship_id, first_id, last_id, start_at, end_at,"
            " messages, kind, scene_share, top_severity, firsts, gist, prompt, at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                e.id,
                rel,
                e.first_id,
                e.last_id,
                iso(e.start_at),
                iso(e.end_at),
                e.messages,
                e.kind,
                e.scene_share,
                e.top_severity,
                json.dumps(list(e.firsts)),
                e.gist,
                e.prompt,
                iso(e.at),
            ),
        )


def all_(conn: sqlite3.Connection, rel: RelationshipId) -> list[Episode]:
    """The newest line for each stretch, oldest stretch first."""
    rows = conn.execute(
        "SELECT * FROM episodes e WHERE relationship_id = ? AND at = (SELECT MAX(at) FROM episodes"
        " WHERE relationship_id = e.relationship_id AND first_id = e.first_id) ORDER BY start_at",
        (rel,),
    ).fetchall()
    return [
        Episode(
            str(r["id"]),
            UtteranceId(str(r["first_id"])),
            UtteranceId(str(r["last_id"])),
            parse_iso(str(r["start_at"])),
            parse_iso(str(r["end_at"])),
            int(r["messages"]),
            str(r["kind"]),
            float(r["scene_share"]),
            int(r["top_severity"]),
            tuple(str(x) for x in json.loads(str(r["firsts"]))),
            str(r["gist"]),
            str(r["prompt"]),
            parse_iso(str(r["at"])),
        )
        for r in rows
    ]
