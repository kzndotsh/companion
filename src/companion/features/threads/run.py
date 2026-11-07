"""Reading what they said for loops worth asking about, and the one tick that decides to ask.

Extraction runs inside the memory pass's batch, after the beliefs, and costs one small call. The
tick runs on a timer, reads the store, asks the pure gate in `gate.py`, and in shadow mode
only records what it would have sent. Nothing here sends a message.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, tzinfo
from typing import TYPE_CHECKING

from companion.core.beliefs.extract import build_user_prompt, index_window
from companion.core.clock import local_zone
from companion.core.extractor import StructuredModel
from companion.core.memory_pass import BATCH, CONTEXT
from companion.core.reachout import (
    DRAFT_SCHEMA,
    PLAN_HELD,
    PLAN_WOULD_SEND,
    Held,
    Kind,
    Mode,
    ReachOut,
    draft_text,
    drafted,
    parse_draft,
)
from companion.core.turn.mentions import LOOP_OFFERED, MentionCandidate, Rank
from companion.core.types import (
    DecisionKind,
    Json,
    RelationshipId,
    Speaker,
    Utterance,
    UtteranceId,
)
from companion.features.threads.gate import Verdict, evaluate
from companion.features.threads.logic import (
    PROMPT,
    SCHEMA,
    Making,
    Thread,
    ThreadKind,
    ThreadState,
    loop_labels,
    loop_note,
    loop_note_ref,
    normalise,
    parse,
    parse_resolved,
    pick_note,
    render_open_loops,
    repeats,
    to_loop,
    to_resolution,
)
from companion.features.threads.met import read_met
from companion.features.threads.store import Threads
from companion.kit.ask import Judge, ask, whole_answer
from companion.kit.features import Feature, Log, Loops, Move, OwnReader, Passing
from companion.kit.reachdraft import DraftKeys, record_draft
from companion.kit.record import Recorder, new_id
from companion.prompts import get
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment, Round
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.initiative")
LOOPS = Judge(
    "loops",
    PROMPT,
    SCHEMA,
    whole_answer,  # `extract_open_loops` reads the items: a bad one is dropped, not the batch
    timeout=120.0,  # a batch of messages a call
    unread="the batch is kept for another try",
)
Draft = Callable[[Thread], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class LoopCounts:
    candidates: int = 0
    stored: int = 0
    rejected: int = 0
    cost_usd: float = 0.0
    resolved: int = 0


async def extract_open_loops(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    window: Mapping[str, Utterance],
    targets: set[UtteranceId],
    when: tuple[datetime, tzinfo],
    note: Log,
    *,
    loose: bool = False,
) -> LoopCounts | None:
    """Record the open loops in the targeted messages, and close the ones they settle. None when
    the call itself failed, so the caller can keep the batch for another try."""
    now, tz = when
    labels = loop_labels(store.part(Threads).loops(rel))
    prompt = build_user_prompt(window, targets, {}, tz) + render_open_loops(labels)
    result = await ask(extractor, LOOPS, prompt)
    if result is None:
        return None
    raw = parse(result.value)
    if raw is None:
        note("open loops: the answer was malformed and was ignored", {"model": result.model})
        return LoopCounts(cost_usd=result.cost_usd)
    known = {normalise(lp.claim) for lp in store.part(Threads).loops(rel)}
    made = Making(rel, now, tz, new_id, loose=loose)
    stored = rejected = 0
    earlier: dict[str, str] = {}
    for i, item in enumerate(raw, start=1):
        outcome = to_loop(item, window, made)
        repeat = repeats(item, labels, earlier)
        earlier[f"N{i}"] = item.kind
        if isinstance(outcome, str):
            rejected += 1
            note(f"open loop rejected: {outcome}", {"claim": item.claim, "quote": item.quote})
        elif repeat is not None:
            rejected += 1
            note(f"open loop rejected: {repeat}", {"claim": item.claim, "quote": item.quote})
        elif normalise(outcome.claim) in known:
            rejected += 1
            note("open loop rejected: already recorded", {"claim": outcome.claim})
        else:
            store.part(Threads).add_loop(outcome)
            known.add(normalise(outcome.claim))
            stored += 1
            note(
                "open loop recorded from their own words",
                {
                    "loop_id": outcome.id,
                    "claim": outcome.claim,
                    "quote": outcome.quote,
                    "follow_up_at": outcome.follow_up_at.isoformat(),
                    "model": result.model,
                    "prompt": PROMPT.ref,
                },
            )
    resolved = _close_resolved(store, result.value, labels, window, now, note)
    log.debug(
        "open loops: %d proposed, %d stored, %d rejected, %d resolved",
        len(raw),
        stored,
        rejected,
        resolved,
    )
    return LoopCounts(len(raw), stored, rejected, result.cost_usd, resolved)


def _close_resolved(  # noqa: PLR0913, PLR0917
    store: Store,
    data: Json,
    labels: Mapping[str, Thread],
    window: Mapping[str, Utterance],
    now: datetime,
    note: Log,
) -> int:
    """Close each loop their new messages settle, so it is never asked about."""
    closed: set[str] = set()
    for item in parse_resolved(data):
        outcome = to_resolution(item, labels, window)
        if isinstance(outcome, str):
            note(f"open loop not closed: {outcome}", {"loop": item.loop, "quote": item.quote})
            continue
        loop, quote = outcome
        if loop.id in closed:
            continue
        closed.add(loop.id)
        store.part(Threads).add_event(
            loop.id, ThreadState.RESOLVED, f"they brought it up: {quote!r}", now
        )
        note(
            f"open loop closed, they brought it up themselves: {loop.claim}",
            {"loop_id": loop.id, "quote": quote, "prompt": PROMPT.ref},
        )
    return len(closed)


@dataclass(slots=True)
class Ticker:
    """Remembers which holds it has already recorded, so a hold that lasts hours is one decision
    and not ninety-six."""

    seen: set[tuple[str, str]] = field(default_factory=set[tuple[str, str]])


DRAFT_DROPPED = "open loop: the check-in draft was dropped, not sent"
KEYS = DraftKeys(DRAFT_DROPPED, PLAN_WOULD_SEND)


async def tick(  # noqa: PLR0913, PLR0917
    store: Store,
    rel: RelationshipId,
    now: datetime,
    tz: tzinfo,
    draft: Draft | None,
    ticker: Ticker,
    *,
    held: Held | None,
) -> Verdict:
    """One look at the open loops, with the shared gate's hold (ADR 0023; None when nothing holds a
    reach-out now). In shadow mode a verdict to send is recorded with a drafted message and the
    loop is marked asked, but nothing is sent. A draft that failed or reads as needy is dropped,
    logged, and that loop is not drafted again (it can still come up when they write)."""
    dropped = {
        str((d.detail or {}).get("loop_id")) for d in store.decisions_with_key(rel, DRAFT_DROPPED)
    }
    loops = [lp for lp in store.part(Threads).loops(rel) if lp.id not in dropped]
    verdict = evaluate(loops, now, tz, held.why if held else None)
    for lp in verdict.expired:
        store.part(Threads).add_event(lp.id, ThreadState.EXPIRED, "past its follow-up horizon", now)
        Recorder.fresh(store, rel, now).decide(
            "open loop expired", {"loop_id": lp.id}, reason=f"open loop expired: {lp.claim}"
        )
    if verdict.loop is None:
        log.debug("initiative: %s", verdict.reason)
        return verdict
    detail: dict[str, Json] = {"loop_id": verdict.loop.id, "claim": verdict.loop.claim}
    if not verdict.send:
        key = (verdict.loop.id, held.what if held else verdict.reason)
        if key not in ticker.seen:
            ticker.seen.add(key)
            reason = f"held, would otherwise reach out about {verdict.loop.claim}: {verdict.reason}"
            Recorder.fresh(store, rel, now).decide(
                PLAN_HELD, detail, reason=reason, kind=DecisionKind.DO_NOTHING
            )
            log.info("initiative held: %s (%s)", verdict.loop.claim, verdict.reason)
        return verdict
    got = drafted(await draft(verdict.loop) if draft is not None else "", "empty")
    text, why = got
    if not text:
        detail["why"] = why
        record_draft(Recorder.fresh(store, rel, now), KEYS, got, detail, "")
        log.info(
            "initiative: the check-in draft about %s was dropped (%s)", verdict.loop.claim, why
        )
        return Verdict(False, f"{DRAFT_DROPPED}: {why}", verdict.loop, verdict.expired)
    store.add_reach_out(
        ReachOut(new_id(), rel, verdict.loop.id, Mode.SHADOW, text, verdict.reason, now)
    )
    store.part(Threads).add_event(
        verdict.loop.id, ThreadState.ASKED, "shadow reach-out, not sent", now
    )
    detail["draft"] = text
    record_draft(
        Recorder.fresh(store, rel, now), KEYS, got, detail, f"shadow, would send: {verdict.reason}"
    )
    log.info("initiative shadow: would send %r about %s", text, verdict.loop.claim)
    return verdict


DRAFT_PROMPT = get("system/openloops-draft")
CHECK_IN = Judge(
    "check-in-draft",
    DRAFT_PROMPT,
    DRAFT_SCHEMA,
    parse_draft,
    timeout=30.0,  # one short message
    unread="an empty draft: the check-in is dropped and that loop is not drafted again",
    spend="initiative",  # every reach-out's drafting is one line in `companion spend`
)


def drafter(extractor: StructuredModel) -> Draft:
    """A function that drafts the check-in for a loop. Any failure gives an empty draft."""

    async def draft(loop: Thread) -> str:
        prompt = f"They said: {loop.quote!r}\nThe thing: {loop.claim}\nKind: {loop.kind}"
        got = await ask(extractor, CHECK_IN, prompt)
        return "" if got is None else draft_text(got.value)

    return draft


MAX_TRIES = 3  # a batch that keeps failing is let go, so plans can never block on one


@dataclass(frozen=True, slots=True)
class Reading:
    """Where the open-loop pass reads from: its batch size, the context before it, and how many
    batches one call may catch up."""

    batch: int
    context: int
    batches: int = 3
    own: tuple[OwnReader, ...] = ()  # also read its own messages in the batch (promises, J12)
    loose: bool = False  # hedged plans become note-only loops (COMPANION_HEDGED_PLANS=loose)


async def catch_up_loops(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    when: tuple[datetime, tzinfo],
    note: Log,
    reading: Reading,
) -> LoopCounts:
    """Read their messages for plans from the open-loop pass's own bookmark (J25). A failed call
    leaves the bookmark where it was, so the same messages are read again next pass; after
    MAX_TRIES failures on one batch it is let go, with the reason logged."""
    now = when[0]
    total = LoopCounts()
    for _ in range(reading.batches):
        batch = store.utterances_after(rel, store.part(Threads).loop_cursor(rel), reading.batch)
        if not batch:
            break
        upto = (batch[-1].at, batch[-1].id)
        targets = {u.id for u in batch if u.speaker is Speaker.USER}
        mine = {u.id for u in batch if u.speaker is Speaker.COMPANION}
        own: set[UtteranceId] = mine if reading.own else set()
        if not targets and not own:
            store.part(Threads).record_loop_run(
                rel, upto, ok=True, reason="none of their messages", at=now
            )
            continue
        window = index_window([*store.history_before(rel, batch[0].at, reading.context), *batch])
        counts = (
            await extract_open_loops(
                store, extractor, rel, window, targets, when, note, loose=reading.loose
            )
            if targets
            else LoopCounts()
        )
        spent: float | None = 0.0
        for read_own in reading.own if own else ():
            more = await read_own(store, extractor, window, own, when, note)
            spent = None if spent is None or more is None else spent + more
        if counts is not None and spent is not None:
            store.part(Threads).record_loop_run(rel, upto, ok=True, reason="read", at=now)
            total = _add(total, replace(counts, cost_usd=counts.cost_usd + spent))
            continue
        tries = store.part(Threads).failed_tries(rel, upto[1]) + 1
        if tries >= MAX_TRIES:
            reason = f"open loops: gave up on a batch after {tries} failed tries"
            store.part(Threads).record_loop_run(rel, upto, ok=True, reason=reason, at=now)
            note(reason, {"messages": len(batch), "upto": upto[1]})
            continue
        store.part(Threads).record_loop_run(
            rel, upto, ok=False, reason=f"failed try {tries}", at=now
        )
        break
    return total


def _add(a: LoopCounts, b: LoopCounts) -> LoopCounts:
    return LoopCounts(
        a.candidates + b.candidates,
        a.stored + b.stored,
        a.rejected + b.rejected,
        a.cost_usd + b.cost_usd,
        a.resolved + b.resolved,
    )


_RANK = {
    ThreadKind.CELEBRATE: Rank.THEIRS,
    ThreadKind.ENCOURAGE: Rank.FACING,
    ThreadKind.FOLLOW_UP: Rank.FOLLOW_UP,
}


def loop_candidate(m: Moment, found: object) -> MentionCandidate | None:
    """The due open loop it would bring up as a note when they write (J15), each at most twice;
    the picker decides whether it does. Once the reply is stored the loop is marked asked, so it is
    never also a reach-out."""
    del found
    c, t = m.c, m.t
    offers = c.store.part(Threads).events_with_key(c.rel, LOOP_OFFERED)
    loop = pick_note(c.store.part(Threads).loops(c.rel), offers, t.now, local_zone())
    note = loop_note(loop) if loop is not None else ""
    if loop is None or not note:
        return None
    detail: dict[str, Json] = {
        "loop_id": loop.id,
        "claim": loop.claim,
        "kind": loop.kind.value,
        "offer": offers.get(loop.id, 0) + 1,
        "note": loop_note_ref(loop),
    }
    asked = functools.partial(
        c.store.part(Threads).add_event,
        loop.id,
        ThreadState.ASKED,
        LOOP_OFFERED,
        t.now,
        key=LOOP_OFFERED,
    )
    return MentionCandidate(
        _RANK[loop.kind], note, False, LOOP_OFFERED, loop.claim, detail, write=asked
    )


# Threads (ADR 0023): today plans of theirs, read in the open-loop batch; a due one is a candidate
# for the one thing brought up when they write.
def reaching(c: Runtime) -> tuple[Move, ...]:
    """Its step in the initiative tick: a plan of theirs that is due comes first (ADR 0021)."""
    ticker = Ticker()
    draft = drafter(c.judge) if c.judge is not None else None

    async def plan(r: Round) -> None:
        verdict = await tick(c.store, c.rel, r.now, r.tz, draft, ticker, held=r.held)
        if verdict.send:
            r.first = Kind.PLAN

    return (Move(Kind.PLAN, plan),)


def pass_loops(p: Passing, own: Sequence[OwnReader]) -> Loops:
    """The open-loop read the memory pass runs, with the own-message readers that ride its batch."""
    reading = Reading(BATCH, CONTEXT, own=tuple(own), loose=p.loose_plans)

    async def read(
        store: Store,
        extractor: StructuredModel,
        rel: RelationshipId,
        when: tuple[datetime, tzinfo],
        note: Log,
    ) -> LoopCounts:
        return await catch_up_loops(store, extractor, rel, when, note, reading)

    return read


OPENLOOPS = Feature(
    "loop",
    loops=pass_loops,
    mention=loop_candidate,
    mention_key=LOOP_OFFERED,
    after_turn=read_met,
    reaching=reaching,
    needs_judge=True,
)
