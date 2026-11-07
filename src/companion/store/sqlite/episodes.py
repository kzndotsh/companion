"""Episodes, read only (the episodes feature writes them; the newest gist of each wins)."""

from __future__ import annotations

import json
import sqlite3

from companion.core.episode import Episode
from companion.core.types import RelationshipId, Severity, UtteranceId
from companion.lib.sqlite.db import parse_iso


def all_(conn: sqlite3.Connection, rel: RelationshipId) -> list[Episode]:
    """The newest gist for each episode, oldest episode first."""
    rows = conn.execute(
        "SELECT * FROM episodes e WHERE relationship_id = ?"
        " AND at = (SELECT MAX(at) FROM episodes WHERE relationship_id = e.relationship_id"
        " AND first_id = e.first_id) ORDER BY start_at",
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
            Severity(int(r["top_severity"])),
            tuple(str(x) for x in json.loads(str(r["firsts"]))),
            str(r["gist"]),
            str(r["prompt"]),
            parse_iso(str(r["at"])),
        )
        for r in rows
    ]
