"""The slow loop: read new conversation, record what it revealed, never touch the reply path.

One pass reads the utterances after the cursor, asks a cheap model for candidate beliefs, and
keeps only those that pass the quote gate. Every acceptance and rejection is a logged decision.
Idempotent: the run log is the cursor, so a crashed or repeated pass re-reads nothing it finished.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, tzinfo
from typing import Protocol

from companion.core.beliefs.dedupe import is_duplicate_candidate
from companion.core.beliefs.extract import (
    PROMPT as USER_PROMPT,
)
from companion.core.beliefs.extract import (
    SCHEMA,
    SYSTEM,
    Candidate,
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
from companion.core.beliefs.self_extract import PROMPT as SELF_PROMPT
from companion.core.beliefs.self_extract import SCHEMA as SELF_SCHEMA
from companion.core.beliefs.self_extract import SYSTEM as SELF_SYSTEM
from companion.core.beliefs.self_extract import parse_views, to_view
from companion.core.clock import local_zone, utc_now
from companion.core.extractor import Extractor
from companion.core.reflect import ReflectRun
from companion.core.types import (
    Belief,
    BeliefId,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.vectors import Embedder
from companion.features.consolidate.run import SameCheck
from companion.features.promises.run import read_promises
from companion.features.threads.run import Reading, catch_up_loops
from companion.loops.embed import embed_missing
from companion.loops.record import Recorder
from companion.memory.views import WANT_KINDS, check_views
from companion.registry import FEATURES
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.slow")
BATCH = 40
CONTEXT = 4


def _id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class ReflectOptions:
    now: datetime | None = None
    ignore: frozenset[BeliefId] = frozenset()
    tz: tzinfo | None = None
    same: SameCheck | None = None  # write-time check against existing memories (ADR 0019)
    promises: bool = False  # read its own messages for promises it made (J12, shadow)
    embed: tuple[Embedder, str] | None = None  # embed new memories after the pass (model name)
    loose_loops: bool = False  # hedged plans become note-only loops (COMPANION_LOOP_NOTES)
    history: _Step | None = None  # read its own messages for stories of its past (ADR 0025)


@dataclass(frozen=True, slots=True)
class ReflectResult:
    ran: bool
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    confirmed: int = 0
    cost_usd: float = 0.0
    upto: tuple[datetime, UtteranceId] | None = None
    views_accepted: int = 0
    views_confirmed: int = 0
    views_rejected: int = 0
    views_checked: int = 0
    views_conflicts: int = 0


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
        Recorder(
            self.store, self.rel, self.session, self.turn, TraceId(self.run_id), self.now
        ).decide(reason, detail)

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


class _Spent(Protocol):
    @property
    def cost_usd(self) -> float: ...


_Step = Callable[[Store, Extractor, RelationshipId, datetime], Awaitable[_Spent]]


# What runs once a pass has stored new memories of theirs, and new views of its own: each feature's
# step, in the registry's order (the map of their life, names, what they were talking about, what
# kind of memory it is; for views, lore).
AFTER_THEIRS: tuple[_Step, ...] = tuple(
    f.after_theirs for f in FEATURES if f.after_theirs is not None
)
AFTER_OWN: tuple[_Step, ...] = tuple(f.after_own for f in FEATURES if f.after_own is not None)


async def reflect_once(  # noqa: PLR0913
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    now: datetime | None = None,
    same: SameCheck | None = None,
    *,
    promises: bool = False,
    embed: tuple[Embedder, str] | None = None,
    loose_loops: bool = False,
    history: _Step | None = None,
) -> ReflectResult:
    options = ReflectOptions(
        now, same=same, promises=promises, embed=embed, loose_loops=loose_loops, history=history
    )
    return await reflect_from(store, extractor, rel, store.reflect_cursor(rel), options)


@dataclass(frozen=True, slots=True)
class _Spec:
    """What differs between reading the user's words and reading the companion's own."""

    system: str
    schema: dict[str, Json]
    parse: Callable[[Json], tuple[list[Candidate], list[Rejection]]]
    make: Callable[
        [Candidate, Mapping[str, Utterance], RelationshipId, datetime, Callable[[], str]],
        Belief | Rejection,
    ]
    speaker: Speaker
    accepted_reason: str
    prompt_ref: str


USER_SPEC = _Spec(
    SYSTEM,
    SCHEMA,
    parse,
    to_belief,
    Speaker.USER,
    "accepted: quote verified verbatim in a user message",
    USER_PROMPT.ref,
)
SELF_SPEC = _Spec(
    SELF_SYSTEM,
    SELF_SCHEMA,
    parse_views,
    to_view,
    Speaker.COMPANION,
    "accepted: a view the companion expressed, quote verified in its own message",
    SELF_PROMPT.ref,
)


@dataclass(frozen=True, slots=True)
class _Counts:
    candidates: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    confirmed: int = 0
    accepted_ids: frozenset[BeliefId] = frozenset()
    cost: float = 0.0
    latency_ms: int = 0
    model: str = "none"


@dataclass(frozen=True, slots=True)
class _Ctx:
    """What both passes share: where to read, who to ask, and how to log."""

    store: Store
    extractor: Extractor
    run: _Pass
    window: Mapping[str, Utterance]
    tz: tzinfo
    same: SameCheck | None = None


async def _stored_as_evidence(ctx: _Ctx, spec: _Spec, made: Belief) -> bool:
    """When a new memory of theirs is the same as an existing one (three pair reads, ADR 0019):
    `on` adds its quote to the existing memory instead of storing it; shadow only logs that."""
    if ctx.same is None or spec is not USER_SPEC or ctx.same.mode == "off":
        return False
    older = await ctx.same.find(ctx.store, ctx.run.rel, made, ctx.run.now)
    if older is None:
        return False
    detail: dict[str, Json] = {"belief_id": older.id, "claim": older.claim, "new": made.claim}
    if ctx.same.mode != "on":
        ctx.run.log("would store as evidence on an existing memory (shadow)", detail)
        return False
    ctx.store.add_evidence(older.id, made.evidence[0])
    ctx.run.log("confirmed: the same as an existing memory, stored as evidence on it", detail)
    return True


async def _extract_pass(
    spec: _Spec,
    ctx: _Ctx,
    targets: list[Utterance],
    known: list[Belief],
    rejected: list[Belief] | None = None,
) -> _Counts:
    store, extractor, run, window, tz = ctx.store, ctx.extractor, ctx.run, ctx.window, ctx.tz
    labelled = known_index(known)
    result = await extractor.extract(
        spec.system,
        build_user_prompt(window, {u.id for u in targets}, labelled, tz, rejected or ()),
        spec.schema,
    )
    candidates, rejections = spec.parse(result.data)
    n_candidates = len(candidates) + len(rejections)
    seen = {normalise(b.claim) for b in known}
    accepted = duplicates = confirmed = 0
    stored: list[Belief] = []
    for c in candidates:
        if c.confirms:
            outcome = to_confirmation(c, window, labelled, spec.speaker)
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
                        "prompt": spec.prompt_ref,
                    },
                )
            continue
        made = spec.make(c, window, run.rel, run.now, _id)
        if isinstance(made, Rejection):
            rejections.append(made)
            continue
        source = made.evidence[0]
        if normalise(made.claim) in seen or is_duplicate_candidate(
            source.utterance_id, source.quote, [*known, *stored, *(rejected or [])]
        ):
            duplicates += 1
            continue
        seen.add(normalise(made.claim))
        if await _stored_as_evidence(ctx, spec, made):
            confirmed += 1
            continue
        store.insert_belief(made)
        stored.append(made)
        accepted += 1
        run.log(
            spec.accepted_reason,
            {
                "belief_id": made.id,
                "claim": made.claim,
                "quote": c.quote,
                "model": result.model,
                "prompt": spec.prompt_ref,
            },
        )
    for r in rejections:
        run.log(f"rejected: {r.reason}", {"candidate": r.raw})
    log.debug(
        "%s pass on %d messages: %d candidates, %d stored, %d rejected, %d duplicates,"
        " %d confirmed, %dms, $%.5f, %s",
        spec.speaker,
        len(targets),
        n_candidates,
        accepted,
        len(rejections),
        duplicates,
        confirmed,
        result.latency_ms,
        result.cost_usd,
        result.model,
    )
    return _Counts(
        n_candidates,
        accepted,
        len(rejections),
        duplicates,
        confirmed,
        frozenset(b.id for b in stored),
        result.cost_usd,
        result.latency_ms,
        result.model,
    )


async def reflect_from(
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    start: tuple[datetime, UtteranceId] | None,
    options: ReflectOptions = ReflectOptions(),  # noqa: B008
) -> ReflectResult:
    """One batch after `start`. Pass None to read from the beginning, for a re-read.

    Two passes over the same batch: beliefs about the user from the user's words, and views the
    companion expressed from its own words. `ignore` names old beliefs that a rebuild is
    replacing, so they do not count as duplicates of their own restatements.
    """
    now = options.now or utc_now()
    batch = store.utterances_after(rel, start, BATCH)
    if not batch:
        return ReflectResult(ran=False)
    upto = (batch[-1].at, batch[-1].id)
    last = batch[-1]
    log.debug(
        "reflect: reading %d messages after %s", len(batch), start[0] if start else "the start"
    )
    user_targets = [u for u in batch if u.speaker is Speaker.USER]
    own_targets = [u for u in batch if u.speaker is Speaker.COMPANION]
    anchor = user_targets[-1] if user_targets else last
    run = _Pass(store, rel, _id(), now, anchor.session_id, anchor.turn_id)
    if not user_targets and not own_targets:
        run.finish(last, len(batch))
        return ReflectResult(ran=True, upto=upto)
    window = index_window([*store.history_before(rel, batch[0].at, CONTEXT), *batch])
    local = options.tz or local_zone()
    ctx = _Ctx(store, extractor, run, window, local, options.same)
    users = _Counts()
    own = _Counts()
    if user_targets:
        known = [b for b in store.user_beliefs(rel) if b.id not in options.ignore]
        users = await _extract_pass(USER_SPEC, ctx, user_targets, known)
    if own_targets:
        own = await _extract_pass(
            SELF_SPEC, ctx, own_targets, store.self_beliefs(rel), store.rejected_views(rel)
        )
    run = replace(
        run,
        model=users.model if user_targets else own.model,
        cost=users.cost + own.cost,
        latency_ms=users.latency_ms + own.latency_ms,
    )
    run.finish(
        last,
        len(batch),
        candidates=users.candidates,
        accepted=users.accepted,
        rejected=users.rejected,
    )
    loops = await catch_up_loops(
        store,
        extractor,
        rel,
        (now, local),
        run.log,
        Reading(
            BATCH,
            CONTEXT,
            promises=read_promises if options.promises else None,
            loose=options.loose_loops,
        ),
    )
    wanted = {b.id for b in store.user_beliefs(rel) if b.kind in WANT_KINDS}
    new_wants = users.accepted_ids & wanted
    check = await check_views(store, extractor, rel, now, recheck=bool(new_wants))
    after = [*(AFTER_THEIRS if users.accepted else ()), *(AFTER_OWN if own.accepted else ())]
    if options.history is not None:
        after.append(options.history)
    labelled = sum([(await step(store, extractor, rel, now)).cost_usd for step in after])
    if users.accepted and options.embed is not None:
        labelled += await _embed_new(store, rel, now, options.embed)
    return ReflectResult(
        True,
        users.accepted,
        users.rejected,
        users.duplicates,
        users.confirmed,
        users.cost + own.cost + check.cost_usd + loops.cost_usd + labelled,
        upto,
        views_accepted=own.accepted,
        views_confirmed=own.confirmed,
        views_rejected=own.rejected,
        views_checked=check.checked,
        views_conflicts=check.conflicts,
    )


async def _embed_new(
    store: Store, rel: RelationshipId, now: datetime, embed: tuple[Embedder, str]
) -> float:
    """Embed the memories this pass stored, so no turn's look-up has to. A failure is logged and
    left for the next pass, or the next look-up, to do."""
    embedder, model = embed
    try:
        return await embed_missing(store, embedder, rel, model, now)
    except Exception as err:
        log.warning("embedding new memories after the pass failed: %r", err)
        return 0.0
