"""The kind of each of the companion's views, in one place: the columns of `view_kinds` are named
here. The lore feature writes through `insert`; the newest label of a view wins (`latest`)."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.core.views import ViewKind
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class KindRow:
    """One label as stored: the view, its kind, and who labelled it (a model and the prompt's
    `name@version`) and when."""

    belief_id: BeliefId
    kind: ViewKind
    model: str
    prompt: str
    at: datetime


def insert(conn: sqlite3.Connection, rel: RelationshipId, rows: Sequence[KindRow]) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO view_kinds (relationship_id, belief_id, kind, model, prompt, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(rel, r.belief_id, r.kind.value, r.model, r.prompt, iso(r.at)) for r in rows],
        )


def latest(conn: sqlite3.Connection, rel: RelationshipId) -> dict[BeliefId, ViewKind]:
    rows = conn.execute(
        "SELECT belief_id, kind FROM view_kinds WHERE relationship_id = ? ORDER BY id", (rel,)
    ).fetchall()
    return {BeliefId(str(r["belief_id"])): ViewKind(str(r["kind"])) for r in rows}
