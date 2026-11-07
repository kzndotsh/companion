"""The kind of each of the companion's views (ADR 0020). Append-only; the newest label wins."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.features.lore.logic import Kind, Labelled
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class ViewKinds:
    """One relationship file's view kinds, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add(
        self,
        rel: RelationshipId,
        labels: Sequence[Labelled],
        *,
        model: str,
        prompt: str,
        at: datetime,
    ) -> None:
        with write_tx(self.conn):
            self.conn.executemany(
                "INSERT INTO view_kinds (relationship_id, belief_id, kind, model, prompt, at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(rel, x.belief_id, x.kind, model, prompt, iso(at)) for x in labels],
            )

    def kinds(self, rel: RelationshipId) -> dict[BeliefId, Kind]:
        rows = self.conn.execute(
            "SELECT belief_id, kind FROM view_kinds WHERE relationship_id = ? ORDER BY id", (rel,)
        ).fetchall()
        return {BeliefId(str(r["belief_id"])): Kind(str(r["kind"])) for r in rows}
