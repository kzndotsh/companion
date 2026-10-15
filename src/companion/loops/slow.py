"""The slow loop: read new conversation, record what it revealed, never touch the reply path.

One pass reads the utterances after the cursor, asks a cheap model for candidate beliefs, and
keeps only those that pass the quote gate. Every acceptance and rejection is a logged decision.
Idempotent: the run log is the cursor, so a crashed or repeated pass re-reads nothing it finished.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, tzinfo

from companion.core.beliefs.dedupe import is_duplicate_candidate
from companion.core.beliefs.extract import (
    SCHEMA,
    SYSTEM,
    Rejection,
    Skip,
    build_user_prompt,
    index_window,
    known_index,
    normalise,
    parse,
    to_belief,
    to_confirmation,
)
from companion.core.extractor import Extractor
from companion.core.reflect import ReflectRun
from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.store.sqlite.store import Store

BATCH = 40
CONTEXT = 4


def _id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class ReflectOptions:
    now: datetime | None = None
    ignore: frozenset[BeliefId] = frozenset()
    tz: tzinfo | None = None


@dataclass(frozen=True, slots=True)
class ReflectResult:
    ran: bool
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    confirmed: int = 0
    cost_usd: float = 0.0
    upto: tuple[datetime, UtteranceId] | None = None


@dataclass(frozen=True, slots=True)
class _Pass:
    """The fixed facts of one pass, so decisions and the run record are built the same way."""

    store: Store
    rel: RelationshipId
    run_id: str
    now: datetime
    session: SessionId
    turn: TurnId
    model: str = "none"
    cost: float = 0.0
    latency_ms: int = 0

    def log(self, reason: str, detail: dict[str, Json]) -> None:
        self.store.append_decision(
            Decision(
                DecisionId(_id()),
                self.rel,
                self.session,
                self.turn,
                TraceId(self.run_id),
                DecisionKind.POLICY,
                reason,
                self.now,
                detail=detail,
            )
        )

    def finish(self, last: Utterance, n_utterances: int, **counts: int) -> None:
        self.store.record_reflect(
            ReflectRun(
                id=self.run_id,
                relationship_id=self.rel,
                upto_at=last.at,
                upto_id=last.id,
                n_utterances=n_utterances,
                n_candidates=counts.get("candidates", 0),
                n_accepted=counts.get("accepted", 0),
                n_rejected=counts.get("rejected", 0),
                model=self.model,
                cost_usd=self.cost,
                latency_ms=self.latency_ms,
                at=self.now,
            )
        )


async def reflect_once(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime | None = None
) -> ReflectResult:
    return await reflect_from(store, extractor, rel, store.reflect_cursor(rel), ReflectOptions(now))


async def reflect_from(
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    start: tuple[datetime, UtteranceId] | None,
    options: ReflectOptions = ReflectOptions(),  # noqa: B008
) -> ReflectResult:
    """One batch after `start`. Pass None to read from the beginning, for a re-read.

    `ignore` names old beliefs that a rebuild is replacing, so they do not count as duplicates
    of their own restatements. The caller closes them once the whole rebuild succeeds.
    """
    now = options.now or datetime.now(UTC)
    batch = store.utterances_after(rel, start, BATCH)
    if not batch:
        return ReflectResult(ran=False)
    upto = (batch[-1].at, batch[-1].id)
    targets = [u for u in batch if u.speaker is Speaker.USER]
    last = batch[-1]
    anchor = targets[-1] if targets else last
    run = _Pass(store, rel, _id(), now, anchor.session_id, anchor.turn_id)
    if not targets:
        run.finish(last, len(batch))
        return ReflectResult(ran=True, upto=upto)
    index = index_window([*store.history_before(rel, batch[0].at, CONTEXT), *batch])
    known = [b for b in store.current_beliefs(rel) if b.id not in options.ignore]
    labelled = known_index(known)
    local = options.tz or datetime.now().astimezone().tzinfo or UTC
    result = await extractor.extract(
        SYSTEM, build_user_prompt(index, {u.id for u in targets}, labelled, local), SCHEMA
    )
    run = replace(run, model=result.model, cost=result.cost_usd, latency_ms=result.latency_ms)
    candidates, rejections = parse(result.data)
    n_candidates = len(candidates) + len(rejections)
    seen = {normalise(b.claim) for b in known}
    accepted = duplicates = confirmed = 0
    stored: list[Belief] = []
    for c in candidates:
        if c.confirms:
            outcome = to_confirmation(c, index, labelled)
            if isinstance(outcome, Rejection):
                rejections.append(outcome)
            elif isinstance(outcome, Skip):
                duplicates += 1
            else:
                store.add_evidence(outcome.belief.id, outcome.evidence)
                confirmed += 1
                run.log(
                    "confirmed: a new restatement keeps the belief fresh",
                    {
                        "belief_id": outcome.belief.id,
                        "claim": outcome.belief.claim,
                        "quote": outcome.evidence.quote,
                        "model": result.model,
                    },
                )
            continue
        made = to_belief(c, index, rel, now, _id)
        if isinstance(made, Rejection):
            rejections.append(made)
            continue
        source = made.evidence[0]
        if normalise(made.claim) in seen or is_duplicate_candidate(
            source.utterance_id, source.quote, [*known, *stored]
        ):
            duplicates += 1
            continue
        seen.add(normalise(made.claim))
        store.insert_belief(made)
        stored.append(made)
        accepted += 1
        run.log(
            "accepted: quote verified verbatim in a user message",
            {"belief_id": made.id, "claim": made.claim, "quote": c.quote, "model": result.model},
        )
    for r in rejections:
        run.log(f"rejected: {r.reason}", {"candidate": r.raw})
    run.finish(
        last, len(batch), candidates=n_candidates, accepted=accepted, rejected=len(rejections)
    )
    return ReflectResult(
        True, accepted, len(rejections), duplicates, confirmed, result.cost_usd, upto
    )
