"""Closing beliefs by hand or by rule. Every closure is a logged decision with its reason."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from companion.core.beliefs.dedupe import duplicate_groups
from companion.core.types import (
    Belief,
    Decision,
    DecisionId,
    DecisionKind,
    RelationshipId,
    TraceId,
)
from companion.store.sqlite.store import Store


def _close(store: Store, b: Belief, reason: str, now: datetime) -> None:
    source = store.get_utterance(b.evidence[0].utterance_id)
    if source is None:
        msg = f"belief {b.id} cites an utterance missing from the ledger"
        raise ValueError(msg)
    store.close_belief(b.id, now)
    store.append_decision(
        Decision(
            DecisionId(uuid.uuid4().hex),
            b.relationship_id,
            source.session_id,
            source.turn_id,
            TraceId(uuid.uuid4().hex),
            DecisionKind.POLICY,
            f"closed belief: {reason}",
            now,
            detail={"belief_id": b.id, "claim": b.claim},
        )
    )


def close_duplicates(store: Store, rel: RelationshipId, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(UTC)
    report: list[str] = []
    for keep, drop in duplicate_groups(store.current_beliefs(rel)):
        for b in drop:
            _close(store, b, f"duplicate of {keep.id[:8]} (same words)", now)
            report.append(f"closed  {b.claim}\n  kept  {keep.claim}")
    return report


def retire(
    store: Store, rel: RelationshipId, id_prefix: str, reason: str, now: datetime | None = None
) -> str:
    matches = [b for b in store.current_beliefs(rel) if b.id.startswith(id_prefix)]
    if len(matches) != 1:
        msg = f"{len(matches)} current beliefs start with {id_prefix!r}; need exactly one"
        raise ValueError(msg)
    _close(store, matches[0], reason, now or datetime.now(UTC))
    return f"closed  {matches[0].claim}"
