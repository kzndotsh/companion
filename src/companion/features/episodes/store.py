"""The times they spent together (J12). Append-only. The table's columns are owned by
`store/sqlite/episodes.py`, which also reads them (`Store.episodes`)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from companion.core.episode import Episode
from companion.core.types import RelationshipId
from companion.store.sqlite import episodes


@dataclass(frozen=True, slots=True)
class Episodes:
    """One relationship file's episodes, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add(self, rel: RelationshipId, e: Episode) -> None:
        episodes.insert(self.conn, rel, e)
