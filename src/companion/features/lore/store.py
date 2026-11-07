"""The kind of each of the companion's views (ADR 0020). Append-only; the newest label wins. The
table's columns are owned by `store/sqlite/view_kinds.py`, which also reads them
(`Store.view_kinds`)."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId
from companion.features.lore.logic import Labelled
from companion.store.sqlite import view_kinds
from companion.store.sqlite.view_kinds import KindRow


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
        view_kinds.insert(
            self.conn, rel, [KindRow(x.belief_id, x.kind, model, prompt, at) for x in labels]
        )
