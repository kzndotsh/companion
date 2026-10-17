"""The decision trail."""

from __future__ import annotations

import json
import sqlite3

from companion.core.types import (
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Json,
    RelationshipId,
    SessionId,
    TraceId,
    TurnId,
)
from companion.store.sqlite.db import iso, parse_iso, write_tx


def _decision(row: sqlite3.Row) -> Decision:
    detail = row["detail"]
    belief = row["belief_id"]
    parsed: dict[str, Json] | None = None
    if detail is not None:
        loaded: Json = json.loads(str(detail))
        if not isinstance(loaded, dict):
            msg = "decision detail must be a JSON object"
            raise TypeError(msg)
        parsed = loaded
    return Decision(
        id=DecisionId(str(row["id"])),
        relationship_id=RelationshipId(str(row["relationship_id"])),
        session_id=SessionId(str(row["session_id"])),
        turn_id=TurnId(str(row["turn_id"])),
        trace_id=TraceId(str(row["trace_id"])),
        kind=DecisionKind(str(row["kind"])),
        reason=str(row["reason"]),
        at=parse_iso(str(row["at"])),
        belief_id=BeliefId(str(belief)) if belief is not None else None,
        detail=parsed,
    )


def append_decision(conn: sqlite3.Connection, d: Decision) -> None:
    detail = json.dumps(d.detail, sort_keys=True, separators=(",", ":")) if d.detail else None
    with write_tx(conn):
        conn.execute(
            "INSERT INTO decisions (id, relationship_id, session_id, turn_id, trace_id, kind,"
            " belief_id, reason, detail, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                d.id,
                d.relationship_id,
                d.session_id,
                d.turn_id,
                d.trace_id,
                d.kind,
                d.belief_id,
                d.reason,
                detail,
                iso(d.at),
            ),
        )


def decisions_for_turn(
    conn: sqlite3.Connection, relationship_id: RelationshipId, turn_id: TurnId
) -> list[Decision]:
    rows = conn.execute(
        "SELECT * FROM decisions WHERE relationship_id = ? AND turn_id = ? ORDER BY at, id",
        (relationship_id, turn_id),
    ).fetchall()
    return [_decision(r) for r in rows]


def decisions_of_kind(
    conn: sqlite3.Connection, relationship_id: RelationshipId, kind: DecisionKind
) -> list[Decision]:
    rows = conn.execute(
        "SELECT * FROM decisions WHERE relationship_id = ? AND kind = ? ORDER BY at, id",
        (relationship_id, kind),
    ).fetchall()
    return [_decision(r) for r in rows]


def turns_since_reaction(conn: sqlite3.Connection, relationship_id: RelationshipId) -> int | None:
    """How many of the user's messages have come since the last reaction, or None if never."""
    row = conn.execute(
        "SELECT at FROM decisions WHERE relationship_id = ? AND reason LIKE 'reacted %'"
        " ORDER BY at DESC, id DESC LIMIT 1",
        (relationship_id,),
    ).fetchone()
    if row is None:
        return None
    count = conn.execute(
        "SELECT COUNT(*) FROM utterances WHERE relationship_id = ? AND speaker = 'user' AND at > ?",
        (relationship_id, str(row["at"])),
    ).fetchone()
    return int(count[0])


def decisions_for_belief(conn: sqlite3.Connection, belief_id: BeliefId) -> list[Decision]:
    """Everything that was ever done with this belief: the surfacing history."""
    rows = conn.execute(
        "SELECT * FROM decisions WHERE belief_id = ? ORDER BY at, id", (belief_id,)
    ).fetchall()
    return [_decision(r) for r in rows]


def closure_reasons(
    conn: sqlite3.Connection, relationship_id: RelationshipId
) -> dict[BeliefId, str]:
    rows = conn.execute(
        "SELECT json_extract(detail, '$.belief_id') AS bid, reason FROM decisions"
        " WHERE relationship_id = ? AND reason LIKE 'closed belief:%' AND bid IS NOT NULL"
        " ORDER BY at, id",
        (relationship_id,),
    ).fetchall()
    return {BeliefId(str(r["bid"])): str(r["reason"]) for r in rows}
