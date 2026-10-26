"""The intimate scene lane's tables (ADR 0026): each memory's place, the patterns read from scenes
with their quotes, their vectors and how far the scenes have been read. Append-only: the newest row
is a memory's place, and a retire is an event."""

from __future__ import annotations

import json
import sqlite3
from array import array
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime

from companion.core.turn.floor import MINOR_KEY
from companion.core.types import BeliefId, RelationshipId, UtteranceId
from companion.core.vectors import Vector
from companion.features.scene_memory.logic import (
    Everyday,
    Excluded,
    Intimate,
    Lane,
    Pattern,
    Place,
    Quote,
    Stance,
    Why,
    lane_of,
)
from companion.lib.sqlite.db import iso, parse_iso, write_tx

SERIOUS = 2  # a listening read this severe means they were sharing something heavy
LISTENING_KEY = "listening"  # the listening judge's decision, with its labels in the detail


@dataclass(frozen=True, slots=True)
class By:
    model: str
    prompt: str
    at: datetime


def _place(row: sqlite3.Row) -> Place:
    lane = Lane(str(row["lane"]))
    if lane is Lane.INTIMATE:
        return Intimate(Stance(str(row["stance"])))
    if lane is Lane.EXCLUDED:
        return Excluded(Why(str(row["why"])))
    return Everyday()


@dataclass(frozen=True, slots=True)
class SceneMemory:
    """One relationship file's scene lane, behind the store's handle (`Store.scene_memory`)."""

    conn: sqlite3.Connection

    def place(self, places: Mapping[BeliefId, Place], by: By) -> None:
        rows = [
            (
                bid,
                lane_of(p).value,
                p.stance.value if isinstance(p, Intimate) else None,
                p.why.value if isinstance(p, Excluded) else None,
                by.model,
                by.prompt,
                iso(by.at),
            )
            for bid, p in places.items()
        ]
        with write_tx(self.conn):
            self.conn.executemany(
                "INSERT INTO scene_lanes (belief_id, lane, stance, why, model, prompt, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

    def places(self, rel: RelationshipId) -> dict[BeliefId, Place]:
        """Each labelled memory's newest place."""
        rows = self.conn.execute(
            "SELECT l.* FROM scene_lanes l JOIN beliefs b ON b.id = l.belief_id"
            " WHERE b.relationship_id = ? ORDER BY l.id",
            (rel,),
        ).fetchall()
        return {BeliefId(str(r["belief_id"])): _place(r) for r in rows}

    def intimate(self, rel: RelationshipId) -> frozenset[BeliefId]:
        """The memories whose place is the intimate lane: never shown outside a scene when on."""
        return frozenset(b for b, p in self.places(rel).items() if isinstance(p, Intimate))

    def facts(
        self, rel: RelationshipId, utterances: Collection[UtteranceId]
    ) -> tuple[frozenset[UtteranceId], frozenset[UtteranceId]]:
        """Of these messages, the ones on a turn the minor check held, and the ones on a turn the
        listening judge read as serious."""
        if not utterances:
            return frozenset(), frozenset()
        rows = self.conn.execute(
            "SELECT u.id,"
            " MAX(d.key = ? AND json_extract(d.detail, '$.minor') = 1) AS held,"
            " MAX(d.key = ? AND json_extract(d.detail, '$.labels.severity') >= ?) AS heavy"
            " FROM utterances u JOIN decisions d"
            " ON d.relationship_id = u.relationship_id AND d.turn_id = u.turn_id"
            " WHERE u.relationship_id = ? AND u.id IN (SELECT value FROM json_each(?))"
            " GROUP BY u.id",
            (MINOR_KEY, LISTENING_KEY, SERIOUS, rel, json.dumps(list(utterances))),
        ).fetchall()
        held = frozenset(UtteranceId(str(r["id"])) for r in rows if r["held"])
        heavy = frozenset(UtteranceId(str(r["id"])) for r in rows if r["heavy"])
        return held, heavy

    def add_pattern(self, rel: RelationshipId, p: Pattern, by: By) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO scene_patterns (id, relationship_id, claim, stance, model, prompt,"
                " recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p.id, rel, p.claim, p.stance.value, by.model, by.prompt, iso(by.at)),
            )
            for q in p.quotes:
                self._quote(p.id, q, by.at)

    def add_quote(self, pattern_id: str, quote: Quote, at: datetime) -> None:
        with write_tx(self.conn):
            self._quote(pattern_id, quote, at)

    def _quote(self, pattern_id: str, quote: Quote, at: datetime) -> None:
        self.conn.execute(
            "INSERT INTO scene_pattern_quotes (pattern_id, scene_key, utterance_id, quote, at)"
            " VALUES (?, ?, ?, ?, ?)",
            (pattern_id, quote.scene, quote.utterance, quote.text, iso(at)),
        )

    def retire(self, pattern_id: str, reason: str, at: datetime) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO scene_pattern_events (pattern_id, state, reason, at)"
                " VALUES (?, 'retired', ?, ?)",
                (pattern_id, reason, iso(at)),
            )

    def patterns(self, rel: RelationshipId) -> list[Pattern]:
        """Every pattern, oldest first, with its quotes and whether it was retired."""
        rows = self.conn.execute(
            "SELECT p.*, EXISTS (SELECT 1 FROM scene_pattern_events e WHERE e.pattern_id = p.id)"
            " AS retired FROM scene_patterns p WHERE p.relationship_id = ?"
            " ORDER BY p.recorded_at, p.id",
            (rel,),
        ).fetchall()
        quotes: dict[str, list[Quote]] = {}
        for q in self.conn.execute(
            "SELECT q.* FROM scene_pattern_quotes q JOIN scene_patterns p ON p.id = q.pattern_id"
            " WHERE p.relationship_id = ? ORDER BY q.id",
            (rel,),
        ).fetchall():
            quotes.setdefault(str(q["pattern_id"]), []).append(
                Quote(
                    UtteranceId(str(q["scene_key"])),
                    UtteranceId(str(q["utterance_id"])),
                    str(q["quote"]),
                )
            )
        return [
            Pattern(
                str(r["id"]),
                str(r["claim"]),
                Stance(str(r["stance"])),
                tuple(quotes.get(str(r["id"]), ())),
                retired=bool(r["retired"]),
            )
            for r in rows
        ]

    def cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        row = self.conn.execute(
            "SELECT upto_at, upto_id FROM scene_reads WHERE relationship_id = ?"
            " ORDER BY id DESC LIMIT 1",
            (rel,),
        ).fetchone()
        if row is None:
            return None
        return parse_iso(str(row["upto_at"])), UtteranceId(str(row["upto_id"]))

    def read_upto(
        self, rel: RelationshipId, upto: tuple[datetime, UtteranceId], at: datetime
    ) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO scene_reads (relationship_id, upto_at, upto_id, at) VALUES (?,?,?,?)",
                (rel, iso(upto[0]), upto[1], iso(at)),
            )

    def add_vectors(self, vectors: Mapping[str, Vector], model: str, at: datetime) -> None:
        with write_tx(self.conn):
            self.conn.executemany(
                "INSERT INTO scene_vectors (pattern_id, model, vector, at) VALUES (?,?,?,?)",
                [(pid, model, array("f", v).tobytes(), iso(at)) for pid, v in vectors.items()],
            )

    def vectors(self, rel: RelationshipId, model: str) -> dict[str, Vector]:
        rows = self.conn.execute(
            "SELECT v.pattern_id, v.vector FROM scene_vectors v"
            " JOIN scene_patterns p ON p.id = v.pattern_id"
            " WHERE p.relationship_id = ? AND v.model = ? ORDER BY v.id",
            (rel, model),
        ).fetchall()
        out: dict[str, Vector] = {}
        for r in rows:
            floats = array("f")
            floats.frombytes(bytes(r["vector"]))
            out[str(r["pattern_id"])] = tuple(floats)
        return out
