"""Recording a decision (ADR 0003, 0006): the one place ids, the trace and the time are filled in.

A decision has a key, which code looks it up by later ("asked their name today?"), and a reason, the
sentence a person reads. The reason is written by code; when no fuller sentence is given it is the
key itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from companion.core.ids import new_id
from companion.core.types import (
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Recorder:
    """Records the decisions of one turn or one pass."""

    store: Store
    rel: RelationshipId
    turn: TurnId
    trace: TraceId
    now: datetime

    @classmethod
    def fresh(cls, store: Store, rel: RelationshipId, now: datetime) -> Recorder:
        """A recorder for work that is no turn of theirs (a tick, a pass): one new id is its turn
        and its trace."""
        run = new_id()
        return cls(store, rel, TurnId(run), TraceId(run), now)

    @classmethod
    def on_turn(cls, store: Store, rel: RelationshipId, turn: TurnId, now: datetime) -> Recorder:
        """A recorder for work about an existing turn, under a new trace."""
        return cls(store, rel, turn, TraceId(new_id()), now)

    def decide(  # noqa: PLR0913
        self,
        key: str,
        detail: dict[str, Json] | None = None,
        *,
        reason: str | None = None,
        kind: DecisionKind = DecisionKind.POLICY,
        at: datetime | None = None,
        belief: BeliefId | None = None,
    ) -> None:
        self.store.append_decision(
            Decision(
                DecisionId(new_id()),
                self.rel,
                self.turn,
                self.trace,
                kind,
                reason or key,
                at or self.now,
                belief_id=belief,
                detail=detail or None,
                key=key,
            )
        )

    def say(
        self, text: str, platform: str, *, frame: Frame = Frame.REAL, at: datetime | None = None
    ) -> None:
        """Store a message the companion sent, as its own: the one recipe for every send (a reply,
        the crisis line, a reminder, a reach-out)."""
        self.store.append_utterance(
            Utterance(
                UtteranceId(new_id()),
                self.rel,
                self.turn,
                Speaker.COMPANION,
                text,
                frame,
                platform,
                at or self.now,
            )
        )
