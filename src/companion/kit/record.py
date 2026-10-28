"""Recording a decision (ADR 0003, 0006): the one place ids, the trace and the time are filled in.

A decision has a key, which code looks it up by later ("asked their name today?"), and a reason, the
sentence a person reads. The reason is written by code; when no fuller sentence is given it is the
key itself.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

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
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Recorder:
    """Records the decisions of one turn or one pass."""

    store: Store
    rel: RelationshipId
    session: SessionId
    turn: TurnId
    trace: TraceId
    now: datetime

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
                DecisionId(uuid.uuid4().hex),
                self.rel,
                self.session,
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
