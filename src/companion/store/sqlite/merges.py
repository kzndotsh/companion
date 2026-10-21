"""Proposed merges of memories about one thing, and the owner's answers (ADR 0019). Append-only."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.store.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Proposal:
    id: int
    members: tuple[BeliefId, ...]
    claim: str
    prompt: str
    at: datetime
    answer: str | None = None


def add(  # noqa: PLR0913, PLR0917
    conn: sqlite3.Connection,
    rel: RelationshipId,
    members: Sequence[BeliefId],
    claim: str,
    prompt: str,
    at: datetime,
) -> int:
    with write_tx(conn):
        cur = conn.execute(
            "INSERT INTO merge_proposals (relationship_id, members, claim, prompt, at)"
            " VALUES (?,?,?,?,?)",
            (rel, json.dumps(list(members)), claim, prompt, iso(at)),
        )
    return int(cur.lastrowid or 0)


def all_(conn: sqlite3.Connection, rel: RelationshipId) -> list[Proposal]:
    rows = conn.execute(
        "SELECT p.*, (SELECT a.answer FROM merge_answers a WHERE a.proposal_id = p.id"
        " ORDER BY a.id DESC LIMIT 1) AS answer FROM merge_proposals p"
        " WHERE p.relationship_id = ? ORDER BY p.id",
        (rel,),
    ).fetchall()
    return [
        Proposal(
            int(r["id"]),
            tuple(BeliefId(str(m)) for m in json.loads(str(r["members"]))),
            str(r["claim"]),
            str(r["prompt"]),
            parse_iso(str(r["at"])),
            str(r["answer"]) if r["answer"] is not None else None,
        )
        for r in rows
    ]


def answer(conn: sqlite3.Connection, proposal_id: int, said: str, at: datetime) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO merge_answers (proposal_id, answer, at) VALUES (?,?,?)",
            (proposal_id, said, iso(at)),
        )
