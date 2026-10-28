"""Slow-loop run log. The most recent run is the cursor."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.memory_pass import PassRun
from companion.core.types import RelationshipId, UtteranceId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


def record_run(conn: sqlite3.Connection, r: PassRun) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO reflect_runs (id, relationship_id, upto_at, upto_id, n_utterances,"
            " n_candidates, n_accepted, n_rejected, model, cost_usd, latency_ms, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.id,
                r.relationship_id,
                iso(r.upto_at),
                r.upto_id,
                r.n_utterances,
                r.n_candidates,
                r.n_accepted,
                r.n_rejected,
                r.model,
                r.cost_usd,
                r.latency_ms,
                iso(r.at),
            ),
        )


def cursor(
    conn: sqlite3.Connection, relationship_id: RelationshipId
) -> tuple[datetime, UtteranceId] | None:
    row = conn.execute(
        "SELECT upto_at, upto_id FROM reflect_runs WHERE relationship_id = ?"
        " ORDER BY rowid DESC LIMIT 1",
        (relationship_id,),
    ).fetchone()
    if row is None:
        return None
    return parse_iso(str(row["upto_at"])), UtteranceId(str(row["upto_id"]))
