"""One relationship's file, behind a handle so callers never touch sqlite3: the ledger and the
tables the whole system reads. A feature's own tables are a class in its `store.py`, reached with
`part`."""

from __future__ import annotations

import dataclasses
import logging
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

from companion.core.ids import new_id
from companion.core.memory_pass import PassRun
from companion.core.prompt.prefix import Prefix
from companion.core.reachout import ReachOut
from companion.core.replay import TurnRecord
from companion.core.spend import SpendEvent
from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Evidence,
    Favorite,
    Flag,
    FlagId,
    Json,
    Label,
    RelationshipId,
    Subject,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.vectors import Vector
from companion.core.views import ViewState, parse_mode
from companion.store.sqlite import (
    beliefs,
    decisions,
    embeddings,
    favorites,
    flags,
    labels,
    ledger,
    memory_pass,
    reach_outs,
    settings,
    turns,
)
from companion.store.sqlite.db import open_db

VIEWS_MODE_KEY = "views.mode"


log = logging.getLogger("companion.store")


class Part(Protocol):
    """A feature's own queries, built from the connection: a class in its `store.py`."""

    def __init__(self, conn: sqlite3.Connection) -> None: ...


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = open_db(path)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def part[P: Part](self, cls: type[P]) -> P:
        """A feature's queries over this file: `store.part(Stories)`. The store holds the ledger
        and the tables the whole system reads; each feature's tables are its own class."""
        return cls(self._conn)

    def append_utterance(self, u: Utterance) -> None:
        ledger.append_utterance(self._conn, u)

    def mark_undelivered(
        self, rel: RelationshipId, text: str, reason: str, now: datetime
    ) -> Utterance | None:
        """Leave a reply the user never received out of what the model reads, and log it."""
        marked = ledger.mark_undelivered(self._conn, rel, text, reason, now)
        if marked is not None:
            self._policy(
                marked,
                "reply not delivered, so it is left out of what the model reads",
                "reply not delivered",
                {"utterance_id": marked.id, "cause": reason},
                now,
            )
        return marked

    def mark_partly_delivered(
        self, rel: RelationshipId, text: str, delivered: str, reason: str, now: datetime
    ) -> Utterance | None:
        """A reply cut off after some of its messages went out: the whole reply leaves what the
        model reads, and what arrived is added beside it, at the same time and turn. Nothing is
        removed; the whole reply stays in the ledger with its mark."""
        marked = ledger.mark_undelivered(self._conn, rel, text, reason, now)
        if marked is None:
            return None
        seen = dataclasses.replace(marked, id=UtteranceId(new_id()), text=delivered)
        ledger.append_utterance(self._conn, seen)
        self._policy(
            marked,
            "reply partly delivered, so the model reads only the part that arrived",
            "reply partly delivered",
            {"utterance_id": marked.id, "kept_as": seen.id, "cause": reason},
            now,
        )
        return seen

    def _policy(
        self, about: Utterance, reason: str, key: str, detail: dict[str, Json], at: datetime
    ) -> None:
        decisions.append_decision(
            self._conn,
            Decision(
                DecisionId(new_id()),
                about.relationship_id,
                about.turn_id,
                TraceId(about.turn_id),
                DecisionKind.POLICY,
                reason,
                at,
                detail=detail,
                key=key,
            ),
        )

    def history_before(self, rel: RelationshipId, before: datetime, limit: int) -> list[Utterance]:
        return ledger.history_before(self._conn, rel, before, limit)

    def save_prefix(self, p: Prefix) -> None:
        turns.save_prefix(self._conn, p)

    def record_turn(self, r: TurnRecord) -> None:
        turns.record_turn(self._conn, r)

    def append_decision(self, d: Decision) -> None:
        decisions.append_decision(self._conn, d)
        if d.belief_id is None:  # the per-belief card lines are in the database, not the log
            suffix = f" | {d.detail}" if d.detail else ""
            log.debug("decision turn=%s %s: %s%s", d.turn_id[:8], d.kind, d.reason, suffix)

    def latest_turn(self, rel: RelationshipId) -> TurnId | None:
        return turns.latest_turn(self._conn, rel)

    def record_message(  # noqa: PLR0913
        self,
        rel: RelationshipId,
        platform: str,
        message_id: str,
        turn: TurnId,
        at: datetime,
        *,
        sent: bool,
    ) -> None:
        turns.record_message(self._conn, rel, platform, message_id, turn, at, sent=sent)

    def turn_of_message(self, rel: RelationshipId, platform: str, message_id: str) -> TurnId | None:
        return turns.turn_of_message(self._conn, rel, platform, message_id)

    def add_flag(self, f: Flag) -> None:
        flags.add_flag(self._conn, f)

    def add_favorite(self, f: Favorite) -> None:
        favorites.add_favorite(self._conn, f)

    def favorites(self, rel: RelationshipId) -> list[Favorite]:
        return favorites.list_favorites(self._conn, rel)

    def flags(self, rel: RelationshipId) -> list[Flag]:
        """The owner's flags, without the ones they took back."""
        return flags.list_flags(self._conn, rel)

    def withdraw_flag(self, flag_id: FlagId, reason: str, at: datetime) -> None:
        flags.withdraw_flag(self._conn, flag_id, reason, at)

    def utterances_after(
        self, rel: RelationshipId, cursor: tuple[datetime, UtteranceId] | None, limit: int
    ) -> list[Utterance]:
        return ledger.utterances_after(self._conn, rel, cursor, limit)

    def insert_belief(self, b: Belief) -> None:
        beliefs.insert_belief(self._conn, b)

    def current_beliefs(self, rel: RelationshipId) -> list[Belief]:
        """Every current belief, about the user and about itself. Most callers want one of two."""
        return beliefs.current_beliefs(self._conn, rel)

    def user_beliefs_as_of(self, rel: RelationshipId, at: datetime) -> list[Belief]:
        """Every belief about the user that was in force at a moment: recorded by then and not yet
        closed. For rebuilding a past turn's card (evals)."""
        return [
            b
            for b in beliefs.all_beliefs(self._conn, rel, Subject.USER)
            if b.recorded_at <= at and (b.valid_until is None or b.valid_until > at)
        ]

    def user_beliefs(self, rel: RelationshipId) -> list[Belief]:
        return [
            b for b in beliefs.current_beliefs(self._conn, rel) if b.subject is not Subject.SELF
        ]

    def self_beliefs(self, rel: RelationshipId) -> list[Belief]:
        return beliefs.current_beliefs(self._conn, rel, Subject.SELF)

    def evidence_days(
        self, rel: RelationshipId, *, include_closed: bool = False
    ) -> dict[BeliefId, int]:
        return beliefs.evidence_days(self._conn, rel, include_closed=include_closed)

    def record_pass(self, r: PassRun) -> None:
        memory_pass.record_run(self._conn, r)

    def pass_cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        return memory_pass.cursor(self._conn, rel)

    def record_spend(self, rel: RelationshipId, event: SpendEvent, at: datetime) -> None:
        settings.record_spend(self._conn, rel, event, at)

    def add_reach_out(self, r: ReachOut) -> None:
        reach_outs.add(self._conn, r)

    def reach_outs(self, rel: RelationshipId, since: datetime | None = None) -> list[ReachOut]:
        """The reach-outs about a plan. Its own reach-outs are `part(Reaches)`."""
        return reach_outs.since(self._conn, rel, since)

    def reply_text(self, rel: RelationshipId, turn: TurnId) -> str:
        row = self._conn.execute(
            "SELECT text FROM utterances WHERE relationship_id = ? AND turn_id = ?"
            " AND speaker = 'companion'",
            (rel, turn),
        ).fetchone()
        return str(row["text"]) if row else ""

    def add_belief_labels(
        self, rel: RelationshipId, found: Sequence[Label], model: str, prompt: str, at: datetime
    ) -> None:
        labels.add(self._conn, rel, found, model=model, prompt=prompt, at=at)

    def belief_labels(self, rel: RelationshipId) -> dict[BeliefId, Label]:
        return labels.latest(self._conn, rel)

    def add_belief_embeddings(
        self, rel: RelationshipId, vectors: Mapping[BeliefId, Vector], model: str, at: datetime
    ) -> None:
        embeddings.add(self._conn, rel, vectors, model=model, at=at)

    def belief_embeddings(self, rel: RelationshipId, model: str) -> dict[BeliefId, Vector]:
        return embeddings.latest(self._conn, rel, model)

    def spend_since(
        self, rel: RelationshipId, since: datetime
    ) -> list[tuple[str, str, int, float]]:
        return settings.spend_since(self._conn, rel, since)

    def turns_since_reaction(self, rel: RelationshipId) -> int | None:
        return decisions.turns_since_reaction(self._conn, rel)

    def decided_since(self, rel: RelationshipId, reason: str, since: datetime) -> bool:
        return decisions.decided_since(self._conn, rel, reason, since)

    def decisions_for_turn(self, rel: RelationshipId, turn: TurnId) -> list[Decision]:
        return decisions.decisions_for_turn(self._conn, rel, turn)

    def decisions_with_key(
        self, rel: RelationshipId, key: str, since: datetime | None = None
    ) -> list[Decision]:
        return decisions.decisions_with_key(self._conn, rel, key, since)

    def get_utterance(self, utterance_id: UtteranceId) -> Utterance | None:
        return ledger.get_utterance(self._conn, utterance_id)

    def close_belief(self, belief_id: BeliefId, at: datetime) -> None:
        beliefs.close_belief(self._conn, belief_id, at)

    def last_support(self, rel: RelationshipId) -> dict[BeliefId, datetime]:
        return beliefs.last_support(self._conn, rel)

    def add_evidence(self, belief_id: BeliefId, evidence: Evidence) -> None:
        beliefs.add_evidence(self._conn, belief_id, evidence)

    def approve_view(self, belief_id: BeliefId, at: datetime) -> None:
        beliefs.approve_view(self._conn, belief_id, at)

    def approved_views(self, rel: RelationshipId) -> set[BeliefId]:
        return beliefs.approved_ids(self._conn, rel)

    def setting(self, rel: RelationshipId, key: str) -> str | None:
        return settings.get_value(self._conn, rel, key)

    def set_setting(self, rel: RelationshipId, key: str, value: str, at: datetime) -> None:
        settings.set_value(self._conn, rel, key, value, at)

    def record_view_check(
        self, belief_id: BeliefId, *, conflicts: bool, detail: dict[str, Json], at: datetime
    ) -> None:
        settings.record_check(self._conn, belief_id, conflicts=conflicts, detail=detail, at=at)

    def view_checks(self, rel: RelationshipId) -> dict[BeliefId, bool]:
        return settings.latest_checks(self._conn, rel)

    def self_beliefs_all(self, rel: RelationshipId) -> list[Belief]:
        """Every view ever recorded, including closed ones. For calibration, not for the card."""
        return beliefs.all_beliefs(self._conn, rel, Subject.SELF)

    def view_state(self, rel: RelationshipId) -> ViewState:
        return ViewState(
            mode=parse_mode(self.setting(rel, VIEWS_MODE_KEY)),
            approved=frozenset(self.approved_views(rel)),
            days=self.evidence_days(rel),
            checks=self.view_checks(rel),
            support=self.last_support(rel),
        )

    def closures(self, rel: RelationshipId) -> dict[BeliefId, decisions.Closure]:
        """Why each closed belief was closed, from the decision log (newest closure wins)."""
        return decisions.closures(self._conn, rel)

    def user_utterance(self, rel: RelationshipId, turn: TurnId) -> Utterance | None:
        return ledger.user_utterance(self._conn, rel, turn)

    def companion_utterance(self, rel: RelationshipId, turn: TurnId) -> Utterance | None:
        return ledger.companion_utterance(self._conn, rel, turn)

    def rejected_views(self, rel: RelationshipId) -> list[Belief]:
        """Views the user (or a flag) retired. Mechanical closures, like dedupe, do not count."""
        closed = decisions.closures(self._conn, rel)
        return [
            b
            for b in beliefs.all_beliefs(self._conn, rel, Subject.SELF)
            if b.valid_until is not None and (c := closed.get(b.id)) and not c.mechanical
        ]


# A database with no messages yet belongs to this relationship. The live one keeps the id it was
# first given, `telegram-<user id>`, from when the bot only ran on Telegram: it is in every row, and
# the tables are append-only, so it stays as a key no one sees (2026-11-04).
FIRST_RELATIONSHIP = RelationshipId("owner")


def relationship_in(db: Path) -> RelationshipId | None:
    """The one relationship a database holds messages for, None when it has none yet. More than
    one stops the caller: this bot talks with one person."""
    if not db.exists():
        return None
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        found = [str(r[0]) for r in conn.execute("SELECT DISTINCT relationship_id FROM utterances")]
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if len(found) > 1:
        msg = f"{db} holds several relationships ({', '.join(found)}); pass --relationship"
        raise SystemExit(msg)
    return RelationshipId(found[0]) if found else None
