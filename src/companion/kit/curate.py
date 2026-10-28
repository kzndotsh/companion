"""Closing beliefs by hand or by rule. Every closure is a logged decision with its reason."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

from companion.core.beliefs.dedupe import duplicate_groups
from companion.core.clock import utc_now
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    RelationshipId,
    TraceId,
)
from companion.core.views import overstated
from companion.kit.record import Recorder
from companion.store.sqlite.decisions import CLOSED
from companion.store.sqlite.store import Store


def close(store: Store, b: Belief, reason: str, now: datetime) -> None:
    _log(store, b, CLOSED, now, f"closed belief: {reason}")
    store.close_belief(b.id, now)


def log_would_close(store: Store, b: Belief, reason: str, now: datetime) -> None:
    """In shadow: what would have been closed, and why. Nothing changes."""
    _log(store, b, "would close belief (shadow)", now, f"would close belief (shadow): {reason}")


def _log(store: Store, b: Belief, key: str, now: datetime, reason: str) -> None:
    source = store.get_utterance(b.evidence[0].utterance_id)
    if source is None:
        msg = f"belief {b.id} cites an utterance missing from the ledger"
        raise ValueError(msg)
    Recorder(
        store, b.relationship_id, source.session_id, source.turn_id, TraceId(uuid.uuid4().hex), now
    ).decide(key, {"belief_id": b.id, "claim": b.claim}, reason=reason)


def close_duplicates(store: Store, rel: RelationshipId, now: datetime | None = None) -> list[str]:
    now = now or utc_now()
    report: list[str] = []
    for keep, drop in duplicate_groups(store.current_beliefs(rel)):
        for b in drop:
            close(store, b, f"duplicate of {keep.id[:8]} (same words)", now)
            report.append(f"closed  {b.claim}\n  kept  {keep.claim}")
    return report


def retire(
    store: Store, rel: RelationshipId, id_prefix: str, reason: str, now: datetime | None = None
) -> str:
    matches = [b for b in store.current_beliefs(rel) if b.id.startswith(id_prefix)]
    if len(matches) != 1:
        msg = f"{len(matches)} current beliefs start with {id_prefix!r}; need exactly one"
        raise ValueError(msg)
    close(store, matches[0], reason, now or utc_now())
    return f"closed  {matches[0].claim}"


def merge(  # noqa: PLR0913
    store: Store,
    rel: RelationshipId,
    id_prefixes: list[str],
    claim: str,
    now: datetime | None = None,
    *,
    kind: BeliefKind | None = None,
    why: str = "at the owner's request",
) -> str:
    """Several beliefs that say one thing become one, worded by the owner, carrying every quote the
    originals had (ADR 0001); the originals are closed as merged into it, never removed (ADR 0002).
    The kind is the first original's; sensitivity and confidence the highest of them."""
    now = now or utc_now()
    current = store.current_beliefs(rel)
    found: list[Belief] = []
    for prefix in id_prefixes:
        matches = [b for b in current if b.id.startswith(prefix)]
        if len(matches) != 1:
            msg = f"{len(matches)} current beliefs start with {prefix!r}; need exactly one"
            raise ValueError(msg)
        found.append(matches[0])
    if len(found) < 2 or not claim.strip():
        msg = "a merge needs two or more beliefs and the merged wording"
        raise ValueError(msg)
    first = found[0]
    evidence = tuple(dict.fromkeys(e for b in found for e in b.evidence))
    merged = replace(
        first,
        id=BeliefId(uuid.uuid4().hex),
        claim=claim.strip(),
        kind=kind or first.kind,
        evidence=evidence,
        confidence=max(b.confidence for b in found),
        sensitivity=max(b.sensitivity for b in found),
        valid_from=min(b.valid_from for b in found),
        recorded_at=now,
    )
    store.insert_belief(merged)
    for b in found:
        close(store, b, f"merged into {merged.id[:8]} {why}", now)
    return f"merged {len(found)} into {merged.id[:8]}  {merged.claim}"


def approve(store: Store, rel: RelationshipId, id_prefix: str, now: datetime | None = None) -> str:
    """The user approves one of the companion's own views, so it reaches the card."""
    from companion.core.types import Subject  # noqa: PLC0415

    now = now or utc_now()
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
    hedge = overstated(view)
    store.approve_view(view.id, now)
    Recorder(store, rel, source.session_id, source.turn_id, TraceId(uuid.uuid4().hex), now).decide(
        "approved by the user: this view now reaches the card",
        {"belief_id": view.id, "claim": view.claim},
    )
    warn = f"\n  note: it said {hedge!r}; the claim is firmer than its words" if hedge else ""
    return f"approved  {view.claim}{warn}"


def retire_implicated_views(
    store: Store, views: list[Belief], now: datetime | None = None
) -> list[str]:
    """Close the views a flag implicates. The caller decides which; most flags implicate none."""
    now = now or utc_now()
    for b in views:
        close(store, b, "the user flagged a turn, and the flag implicates this view", now)
    return [b.claim for b in views]
