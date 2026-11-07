"""The times they spent together (J12). Append-only. Reading them is `Store.episodes`."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from companion.core.episode import Episode
from companion.core.types import RelationshipId
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class Episodes:
    """One relationship file's episodes, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add(self, rel: RelationshipId, e: Episode) -> None:
        with write_tx(self.conn):
            self.conn.execute(
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
