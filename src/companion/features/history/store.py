"""Its own history (ADR 0025): the stories, what the canon check made of each, their vectors and how
far its messages have been read. Append-only: the newest event is a story's standing."""

from __future__ import annotations

import sqlite3
from array import array
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import Frame, RelationshipId, UtteranceId
from companion.core.vectors import Vector
from companion.features.history.logic import Recorded, Ruling, Standing, Story, StoryId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class By:
    """Who decided: the model and prompt behind a story or an event ("owner" for a retire)."""

    model: str
    prompt: str
    at: datetime


@dataclass(frozen=True, slots=True)
class Stories:
    """One relationship file's stories, behind the store's handle (`Store.stories`)."""

    conn: sqlite3.Connection

    def add(self, s: Story, by: By) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO stories (id, relationship_id, utterance_id, quote, claim, frame,"
                " said_at, model, prompt, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    s.id,
                    s.relationship_id,
                    s.utterance_id,
                    s.quote,
                    s.claim,
                    s.frame.value,
                    iso(s.at),
                    by.model,
                    by.prompt,
                    iso(by.at),
                ),
            )

    def rule(self, story: StoryId, r: Ruling, by: By) -> None:
        """Record what the canon check made of a story, or the owner's retire."""
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO story_events (story_id, standing, verdict, of_story, reason, model,"
                " prompt, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    story,
                    r.standing.value,
                    r.verdict.value if r.verdict is not None else None,
                    r.of,
                    r.reason,
                    by.model,
                    by.prompt,
                    iso(by.at),
                ),
            )

    def recorded(self, rel: RelationshipId) -> list[Recorded]:
        """Every story, oldest first, with its newest event and the stories kept as evidence."""
        rows = self.conn.execute(
            "SELECT s.*, e.standing, e.of_story, e.reason FROM stories s LEFT JOIN story_events e"
            " ON e.id = (SELECT MAX(id) FROM story_events WHERE story_id = s.id)"
            " WHERE s.relationship_id = ? ORDER BY s.said_at, s.id",
            (rel,),
        ).fetchall()
        bare = [
            Recorded(
                Story(
                    StoryId(str(r["id"])),
                    RelationshipId(str(r["relationship_id"])),
                    UtteranceId(str(r["utterance_id"])),
                    str(r["quote"]),
                    str(r["claim"]),
                    Frame(str(r["frame"])),
                    parse_iso(str(r["said_at"])),
                ),
                Standing(str(r["standing"])) if r["standing"] is not None else None,
                StoryId(str(r["of_story"])) if r["of_story"] is not None else None,
                str(r["reason"] or ""),
            )
            for r in rows
        ]
        tellings: dict[StoryId, list[Story]] = {}
        for x in bare:
            if x.standing is Standing.EVIDENCE and x.of is not None:
                tellings.setdefault(x.of, []).append(x.story)
        return [
            Recorded(x.story, x.standing, x.of, x.reason, tuple(tellings.get(x.story.id, ())))
            for x in bare
        ]

    def cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        row = self.conn.execute(
            "SELECT upto_at, upto_id FROM story_reads WHERE relationship_id = ?"
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
                "INSERT INTO story_reads (relationship_id, upto_at, upto_id, at) VALUES (?,?,?,?)",
                (rel, iso(upto[0]), upto[1], iso(at)),
            )

    def add_vectors(self, vectors: Mapping[StoryId, Vector], model: str, at: datetime) -> None:
        with write_tx(self.conn):
            self.conn.executemany(
                "INSERT INTO story_vectors (story_id, model, vector, at) VALUES (?,?,?,?)",
                [(sid, model, array("f", v).tobytes(), iso(at)) for sid, v in vectors.items()],
            )

    def vectors(self, rel: RelationshipId, model: str) -> dict[StoryId, Vector]:
        rows = self.conn.execute(
            "SELECT v.story_id, v.vector FROM story_vectors v JOIN stories s ON s.id = v.story_id"
            " WHERE s.relationship_id = ? AND v.model = ? ORDER BY v.id",
            (rel, model),
        ).fetchall()
        out: dict[StoryId, Vector] = {}
        for r in rows:
            floats = array("f")
            floats.frombytes(bytes(r["vector"]))
            out[StoryId(str(r["story_id"]))] = tuple(floats)
        return out
