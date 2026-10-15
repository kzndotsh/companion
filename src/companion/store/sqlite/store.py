"""One relationship's file, behind a handle so callers never touch sqlite3."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from companion.core.prompt.prefix import Prefix
from companion.core.reflect import ReflectRun
from companion.core.replay import TurnRecord
from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    Evidence,
    Flag,
    Json,
    RelationshipId,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.views import ViewState, parse_mode
from companion.store.sqlite import beliefs, decisions, flags, ledger, reflect, settings, turns
from companion.store.sqlite.db import connect, migrate

VIEWS_MODE_KEY = "views.mode"


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = connect(path)
        migrate(self._conn)

    def close(self) -> None:
        self._conn.close()

    def append_utterance(self, u: Utterance) -> None:
        ledger.append_utterance(self._conn, u)

    def history_before(self, rel: RelationshipId, before: datetime, limit: int) -> list[Utterance]:
        return ledger.history_before(self._conn, rel, before, limit)

    def save_prefix(self, p: Prefix) -> None:
        turns.save_prefix(self._conn, p)

    def record_turn(self, r: TurnRecord) -> None:
        turns.record_turn(self._conn, r)

    def append_decision(self, d: Decision) -> None:
        decisions.append_decision(self._conn, d)

    def latest_turn(self, rel: RelationshipId) -> TurnId | None:
        return turns.latest_turn(self._conn, rel)

    def add_flag(self, f: Flag) -> None:
        flags.add_flag(self._conn, f)

    def flags(self, rel: RelationshipId) -> list[Flag]:
        return flags.list_flags(self._conn, rel)

    def utterances_after(
        self, rel: RelationshipId, cursor: tuple[datetime, UtteranceId] | None, limit: int
    ) -> list[Utterance]:
        return ledger.utterances_after(self._conn, rel, cursor, limit)

    def insert_belief(self, b: Belief) -> None:
        beliefs.insert_belief(self._conn, b)

    def current_beliefs(self, rel: RelationshipId) -> list[Belief]:
        """Every current belief, about the user and about itself. Most callers want one of two."""
        return beliefs.current_beliefs(self._conn, rel)

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

    def record_reflect(self, r: ReflectRun) -> None:
        reflect.record_run(self._conn, r)

    def reflect_cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        return reflect.cursor(self._conn, rel)

    def decisions_for_turn(self, rel: RelationshipId, turn: TurnId) -> list[Decision]:
        return decisions.decisions_for_turn(self._conn, rel, turn)

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

    def closure_reasons(self, rel: RelationshipId) -> dict[BeliefId, str]:
        """Why each closed belief was closed, from the decision log (newest reason wins)."""
        return decisions.closure_reasons(self._conn, rel)

    def user_utterance(self, rel: RelationshipId, turn: TurnId) -> Utterance | None:
        return ledger.user_utterance(self._conn, rel, turn)

    def companion_utterance(self, rel: RelationshipId, turn: TurnId) -> Utterance | None:
        return ledger.companion_utterance(self._conn, rel, turn)

    def rejected_views(self, rel: RelationshipId) -> list[Belief]:
        """Views the user (or a flag) retired. Mechanical closures, like dedupe, do not count."""
        reasons = decisions.closure_reasons(self._conn, rel)
        mechanical = ("closed belief: duplicate of", "closed belief: replaced by a rebuild")
        return [
            b
            for b in beliefs.all_beliefs(self._conn, rel, Subject.SELF)
            if b.valid_until is not None
            and (r := reasons.get(b.id, ""))
            and not r.startswith(mechanical)
        ]
