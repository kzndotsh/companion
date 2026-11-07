"""The intimate scene lane's tables (ADR 0026): each memory's place, the patterns read from scenes
with their quotes, their vectors and how far the scenes have been read. Append-only: the newest row
is a memory's place, and a retire is an event."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime

from companion.core.lane import Lane
from companion.core.turn.floor import MINOR_KEY, MINOR_PATH
from companion.core.turn.listening import LISTENING_KEY, SEVERITY_PATH
from companion.core.types import HEAVY_AT, BeliefId, RelationshipId, UtteranceId
from companion.core.vectors import Vector, from_blob, to_blob
from companion.features.intimate.logic import (
    Everyday,
    Excluded,
    Intimate,
    Pattern,
    Place,
    Quote,
    Stance,
    Why,
    lane_of,
)
from companion.lib.sqlite.db import iso, write_tx
from companion.store.sqlite import bookmark, lanes
from companion.store.sqlite.lanes import LaneRow


@dataclass(frozen=True, slots=True)
class By:
    model: str
    prompt: str
    at: datetime


def _place(row: LaneRow) -> Place:
    lane = Lane(row.lane)
    if lane is Lane.INTIMATE:
        return Intimate(Stance(str(row.stance)))
    if lane is Lane.EXCLUDED:
        return Excluded(Why(str(row.why)))
    return Everyday()


@dataclass(frozen=True, slots=True)
class IntimateMemory:
    """One relationship file's scene lane, behind the store's handle (`Store.intimate_memory`)."""

    conn: sqlite3.Connection

    def place(self, places: Mapping[BeliefId, Place], by: By) -> None:
        lanes.insert(
            self.conn,
            [
                LaneRow(
                    bid,
                    lane_of(p).value,
                    p.stance.value if isinstance(p, Intimate) else None,
                    p.why.value if isinstance(p, Excluded) else None,
                    by.model,
                    by.prompt,
                    iso(by.at),
                )
                for bid, p in places.items()
            ],
        )

    def places(self, rel: RelationshipId) -> dict[BeliefId, Place]:
        """Each labelled memory's newest place."""
        return {bid: _place(r) for bid, r in lanes.newest(self.conn, rel).items()}

    def doubted_before(self, rel: RelationshipId, prompt: str) -> frozenset[BeliefId]:
        """Memories whose newest place is a doubt reached under another version of the prompt."""
        return frozenset(
            bid
            for bid, r in lanes.newest(self.conn, rel).items()
            if r.why == Why.DOUBT.value and r.prompt != prompt
        )

    def facts(
        self, rel: RelationshipId, utterances: Collection[UtteranceId]
    ) -> tuple[frozenset[UtteranceId], frozenset[UtteranceId]]:
        """Of these messages, the ones on a turn the minor check held, and the ones on a turn the
        listening judge read as serious."""
        if not utterances:
            return frozenset(), frozenset()
        rows = self.conn.execute(
            "SELECT u.id,"
            " MAX(d.key = ? AND json_extract(d.detail, ?) = 1) AS held,"
            " MAX(d.key = ? AND json_extract(d.detail, ?) >= ?) AS heavy"
            " FROM utterances u JOIN decisions d"
            " ON d.relationship_id = u.relationship_id AND d.turn_id = u.turn_id"
            " WHERE u.relationship_id = ? AND u.id IN (SELECT value FROM json_each(?))"
            " GROUP BY u.id",
            (
                MINOR_KEY,
                MINOR_PATH,
                LISTENING_KEY,
                SEVERITY_PATH,
                HEAVY_AT,
                rel,
                json.dumps(list(utterances)),
            ),
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

    def cursor(self, rel: RelationshipId) -> bookmark.Place | None:
        return bookmark.newest(self.conn, "scene_reads", rel)

    def read_upto(self, rel: RelationshipId, upto: bookmark.Place, at: datetime) -> None:
        bookmark.mark(self.conn, "scene_reads", rel, upto, at)

    def add_vectors(self, vectors: Mapping[str, Vector], model: str, at: datetime) -> None:
        with write_tx(self.conn):
            self.conn.executemany(
                "INSERT INTO scene_vectors (pattern_id, model, vector, at) VALUES (?,?,?,?)",
                [(pid, model, to_blob(v), iso(at)) for pid, v in vectors.items()],
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
            out[str(r["pattern_id"])] = from_blob(r["vector"])
        return out
