"""One relationship's file, behind a handle so callers never touch sqlite3."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from companion.core.callbacks import Check
from companion.core.invented import Statement
from companion.core.mood import Effect, Said
from companion.core.openloops import LoopState, OpenLoop
from companion.core.promises import Promise
from companion.core.prompt.prefix import Prefix
from companion.core.reflect import ReflectRun
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
from companion.features.context import store as contexts
from companion.features.episodes import store as episodes
from companion.features.lore.logic import Kind as ViewKind
from companion.features.lore.logic import Labelled as ViewLabel
from companion.features.names import store as names
from companion.features.names.logic import Row as NameRow
from companion.features.reminders import store as reminders
from companion.features.reminders.store import Reminder
from companion.store.sqlite import (
    beliefs,
    callbacks,
    decisions,
    embeddings,
    favorites,
    flags,
    invented,
    labels,
    ledger,
    memory_checks,
    merges,
    mood,
    open_loops,
    promises,
    reflect,
    settings,
    turns,
    view_kinds,
)
from companion.store.sqlite.db import open_db
from companion.store.sqlite.open_loops import ReachOut
from companion.store.sqlite.promises import Recorded as RecordedPromise

VIEWS_MODE_KEY = "views.mode"


log = logging.getLogger("companion.store")


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = open_db(path)

    def close(self) -> None:
        self._conn.close()

    def append_utterance(self, u: Utterance) -> None:
        ledger.append_utterance(self._conn, u)

    def mark_undelivered(
        self, rel: RelationshipId, text: str, reason: str, now: datetime
    ) -> Utterance | None:
        """Leave a reply the user never received out of what the model reads, and log it."""
        marked = ledger.mark_undelivered(self._conn, rel, text, reason, now)
        if marked is not None:
            decisions.append_decision(
                self._conn,
                Decision(
                    DecisionId(uuid.uuid4().hex),
                    rel,
                    marked.session_id,
                    marked.turn_id,
                    TraceId(marked.turn_id),
                    DecisionKind.POLICY,
                    "reply not delivered, so it is left out of what the model reads",
                    now,
                    detail={"utterance_id": marked.id, "cause": reason},
                    key="reply not delivered",
                ),
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
        seen = dataclasses.replace(marked, id=UtteranceId(uuid.uuid4().hex), text=delivered)
        ledger.append_utterance(self._conn, seen)
        decisions.append_decision(
            self._conn,
            Decision(
                DecisionId(uuid.uuid4().hex),
                rel,
                marked.session_id,
                marked.turn_id,
                TraceId(marked.turn_id),
                DecisionKind.POLICY,
                "reply partly delivered, so the model reads only the part that arrived",
                now,
                detail={"utterance_id": marked.id, "kept_as": seen.id, "cause": reason},
                key="reply partly delivered",
            ),
        )
        return seen

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

    def record_reflect(self, r: ReflectRun) -> None:
        reflect.record_run(self._conn, r)

    def reflect_cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        return reflect.cursor(self._conn, rel)

    def record_spend(self, rel: RelationshipId, event: SpendEvent, at: datetime) -> None:
        settings.record_spend(self._conn, rel, event, at)
        log.debug(
            "spend %s %s $%.5f in=%d",
            event.purpose,
            event.model,
            event.cost_usd,
            event.input_tokens,
        )

    def add_open_loop(self, loop: OpenLoop) -> None:
        open_loops.add_loop(self._conn, loop)
        log.debug("open loop recorded: %s (follow up %s)", loop.claim, loop.follow_up_at)

    def open_loop_event(self, loop_id: str, state: LoopState, reason: str, at: datetime) -> None:
        open_loops.add_event(self._conn, loop_id, state, reason, at)

    def loop_events_with_reason(self, rel: RelationshipId, reason: str) -> dict[str, int]:
        return open_loops.events_with_reason(self._conn, rel, reason)

    def record_loop_run(
        self,
        rel: RelationshipId,
        upto: tuple[datetime, UtteranceId],
        *,
        ok: bool,
        reason: str,
        at: datetime,
    ) -> None:
        open_loops.record_loop_run(self._conn, rel, upto, ok=ok, reason=reason, at=at)

    def loop_cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        return open_loops.loop_cursor(self._conn, rel)

    def loop_failed_tries(self, rel: RelationshipId, upto_id: UtteranceId) -> int:
        return open_loops.failed_tries(self._conn, rel, upto_id)

    def open_loops(self, rel: RelationshipId) -> list[OpenLoop]:
        return open_loops.loops(self._conn, rel)

    def add_reach_out(self, r: ReachOut) -> None:
        open_loops.add_reach_out(self._conn, r)

    def reach_outs(self, rel: RelationshipId, since: datetime | None = None) -> list[ReachOut]:
        return open_loops.reach_outs_since(self._conn, rel, since)

    def callbacks_unchecked(
        self, rel: RelationshipId, since: datetime
    ) -> list[callbacks.Unchecked]:
        return callbacks.unchecked(self._conn, rel, since)

    def add_callback_check(  # noqa: PLR0913, PLR0917
        self,
        rel: RelationshipId,
        turn: TurnId,
        check: Check,
        judge: str,
        prompt: str,
        at: datetime,
    ) -> None:
        callbacks.add(self._conn, rel, turn, check, judge, prompt, at)

    def reply_text(self, rel: RelationshipId, turn: TurnId) -> str:
        row = self._conn.execute(
            "SELECT text FROM utterances WHERE relationship_id = ? AND turn_id = ?"
            " AND speaker = 'companion'",
            (rel, turn),
        ).fetchone()
        return str(row["text"]) if row else ""

    def add_memory_check(  # noqa: PLR0913
        self,
        rel: RelationshipId,
        belief_id: BeliefId,
        other_id: BeliefId | None,
        reads: Sequence[str | None],
        verdict: str,
        *,
        prompt: str,
        at: datetime,
    ) -> int:
        return memory_checks.add(
            self._conn, rel, belief_id, other_id, reads=reads, verdict=verdict, prompt=prompt, at=at
        )

    def checked_memories(
        self, rel: RelationshipId, prompt: str = "system/memory-check"
    ) -> set[BeliefId]:
        return memory_checks.checked(self._conn, rel, prompt)

    def unanswered_checks(
        self, rel: RelationshipId, verdicts: Sequence[str]
    ) -> list[memory_checks.MemoryCheck]:
        return memory_checks.unanswered(self._conn, rel, verdicts)

    def answer_check(self, check_id: int, said: str, at: datetime) -> None:
        memory_checks.answer(self._conn, check_id, said, at)

    def add_merge_proposal(
        self,
        rel: RelationshipId,
        members: Sequence[BeliefId],
        claim: str,
        *,
        prompt: str,
        at: datetime,
    ) -> int:
        return merges.add(self._conn, rel, members, claim, prompt, at)

    def add_belief_context(
        self, rel: RelationshipId, belief_id: BeliefId, context: str, *, prompt: str, at: datetime
    ) -> None:
        contexts.add(self._conn, rel, belief_id, context, prompt, at)

    def belief_contexts(self, rel: RelationshipId) -> dict[BeliefId, str]:
        return contexts.latest(self._conn, rel)

    def add_episode(self, rel: RelationshipId, e: episodes.Episode) -> None:
        episodes.add(self._conn, rel, e)

    def episodes(self, rel: RelationshipId) -> list[episodes.Episode]:
        return episodes.all_(self._conn, rel)

    def merge_proposals(self, rel: RelationshipId) -> list[merges.Proposal]:
        return merges.all_(self._conn, rel)

    def answer_merge(self, proposal_id: int, said: str, at: datetime) -> None:
        merges.answer(self._conn, proposal_id, said, at)

    def add_names(  # noqa: PLR0913
        self,
        rel: RelationshipId,
        rows: Sequence[NameRow],
        read: Iterable[BeliefId],
        *,
        model: str,
        prompt: str,
        at: datetime,
    ) -> None:
        names.add(self._conn, rel, rows, read, model=model, prompt=prompt, at=at)

    def name_rows(self, rel: RelationshipId) -> list[NameRow]:
        return names.rows(self._conn, rel)

    def names_read(self, rel: RelationshipId) -> set[BeliefId]:
        return names.read(self._conn, rel)

    def add_view_kinds(
        self,
        rel: RelationshipId,
        labels: Sequence[ViewLabel],
        *,
        model: str,
        prompt: str,
        at: datetime,
    ) -> None:
        view_kinds.add(self._conn, rel, labels, model=model, prompt=prompt, at=at)

    def view_kinds(self, rel: RelationshipId) -> dict[BeliefId, ViewKind]:
        return view_kinds.kinds(self._conn, rel)

    def invented_unchecked(self, rel: RelationshipId, since: datetime) -> list[invented.Unchecked]:
        return invented.unchecked(self._conn, rel, since)

    def add_invented_check(  # noqa: PLR0913
        self,
        rel: RelationshipId,
        turn: TurnId,
        statements: list[Statement],
        *,
        judge: str,
        prompt: str,
        at: datetime,
    ) -> None:
        invented.add(self._conn, rel, turn, statements, judge=judge, prompt=prompt, at=at)

    def invented_candidates(self, rel: RelationshipId, start: datetime) -> list[dict[str, object]]:
        return invented.candidates(self._conn, rel, start)

    def invented_since(
        self, rel: RelationshipId, start: datetime
    ) -> list[tuple[str, list[Statement]]]:
        return invented.since(self._conn, rel, start)

    def add_reminder(self, r: Reminder) -> None:
        reminders.add(self._conn, r)

    def reminder_event(self, reminder_id: str, state: str, reason: str, at: datetime) -> None:
        reminders.event(self._conn, reminder_id, state, reason, at)

    def claim_reminder(self, reminder_id: str, at: datetime) -> bool:
        return reminders.claim(self._conn, reminder_id, at)

    def reminders(self, rel: RelationshipId) -> list[Reminder]:
        return reminders.all_(self._conn, rel)

    def add_promise(self, p: Promise, *, model: str, prompt: str, at: datetime) -> None:
        promises.add(self._conn, p, model=model, prompt=prompt, at=at)

    def mark_promise(self, promise_id: str, mark: str, reason: str, at: datetime) -> None:
        promises.mark(self._conn, promise_id, mark, reason, at)

    def promises(self, rel: RelationshipId) -> list[RecordedPromise]:
        return promises.recorded(self._conn, rel)

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

    def add_mood_effects(self, rel: RelationshipId, effects: Sequence[Effect]) -> None:
        mood.add(self._conn, rel, effects)

    def mood_effects_since(self, rel: RelationshipId, start: datetime) -> list[Effect]:
        return mood.since(self._conn, rel, start)

    def said_since(self, rel: RelationshipId, start: datetime) -> list[Said]:
        return mood.said_since(self._conn, rel, start)

    def times_since(self, rel: RelationshipId, start: datetime) -> list[datetime]:
        return mood.times_since(self._conn, rel, start)

    def callback_checks_since(
        self, rel: RelationshipId, start: datetime
    ) -> list[tuple[TurnId, Check]]:
        return callbacks.since(self._conn, rel, start)

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

    def decisions_of_kind(self, rel: RelationshipId, kind: DecisionKind) -> list[Decision]:
        return decisions.decisions_of_kind(self._conn, rel, kind)

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
