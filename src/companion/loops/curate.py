"""Closing beliefs by hand or by rule. Every closure is a logged decision with its reason."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, tzinfo

from companion.core.beliefs.dedupe import duplicate_groups
from companion.core.extractor import Extractor
from companion.core.types import (
    Belief,
    Decision,
    DecisionId,
    DecisionKind,
    RelationshipId,
    TraceId,
)
from companion.loops.slow import ReflectOptions, reflect_from
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


async def rebuild(
    store: Store, extractor: Extractor, rel: RelationshipId, tz: tzinfo | None = None
) -> str:
    """Restate every belief from the whole ledger under the current extraction rules.

    The old beliefs are closed only after every batch has succeeded, so a failure part-way leaves
    them in force. They stay on disk, closed, with the reason logged.
    """
    old = store.user_beliefs(rel)
    options = ReflectOptions(ignore=frozenset(b.id for b in old), tz=tz)
    start = None
    added = 0
    while True:
        result = await reflect_from(store, extractor, rel, start, options)
        if not result.ran:
            break
        added += result.accepted
        start = result.upto
    now = datetime.now(UTC)
    for b in old:
        _close(store, b, "replaced by a rebuild under improved extraction rules", now)
    return f"rebuilt: {added} beliefs added, {len(old)} replaced"


def approve(store: Store, rel: RelationshipId, id_prefix: str, now: datetime | None = None) -> str:
    """The user approves one of the companion's own views, so it reaches the card."""
    from companion.core.types import Subject  # noqa: PLC0415

    now = now or datetime.now(UTC)
    matches = [
        b
        for b in store.self_beliefs(rel)
        if b.id.startswith(id_prefix) and b.subject is Subject.SELF
    ]
    if len(matches) != 1:
        msg = f"{len(matches)} current views start with {id_prefix!r}; need exactly one"
        raise ValueError(msg)
    view = matches[0]
    source = store.get_utterance(view.evidence[0].utterance_id)
    if source is None:
        msg = f"view {view.id} cites an utterance missing from the ledger"
        raise ValueError(msg)
    store.approve_view(view.id, now)
    store.append_decision(
        Decision(
            DecisionId(uuid.uuid4().hex),
            rel,
            source.session_id,
            source.turn_id,
            TraceId(uuid.uuid4().hex),
            DecisionKind.POLICY,
            "approved by the user: this view now reaches the card",
            now,
            detail={"belief_id": view.id, "claim": view.claim},
        )
    )
    return f"approved  {view.claim}"
