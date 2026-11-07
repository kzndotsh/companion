"""What they were talking about when each memory was said (J51). Append-only. The table's columns
are owned by `store/sqlite/belief_context.py`, which also reads them (`Store.belief_contexts`)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.store.sqlite import belief_context
from companion.store.sqlite.belief_context import ContextRow


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
        belief_context.insert(self.conn, rel, ContextRow(belief_id, context, prompt, at))
