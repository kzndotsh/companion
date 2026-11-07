"""What they were talking about when each memory was said (J51). Append-only. Reading them is
`Store.belief_contexts`."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class BeliefContexts:
    """One relationship file's belief contexts, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add(
        self,
        rel: RelationshipId,
        belief_id: BeliefId,
        context: str,
        *,
        prompt: str,
        at: datetime,
    ) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO belief_context (relationship_id, belief_id, context, prompt, at)"
                " VALUES (?,?,?,?,?)",
                (rel, belief_id, context, prompt, iso(at)),
            )
