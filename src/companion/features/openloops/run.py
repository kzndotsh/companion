"""Reading what they said for loops worth asking about, and the one tick that decides to ask.

Extraction runs inside the slow loop's batch, after the beliefs, and costs one small call. The tick
runs on a timer, reads the store, asks the pure gate in `gate.py`, and in shadow mode
only records what it would have sent. Nothing here sends a message.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING

from companion.core.beliefs.extract import build_user_prompt, index_window
from companion.core.clock import local_midnight, local_zone
from companion.core.extractor import Extractor
from companion.core.frames import scene_frame
from companion.core.reachout import Caps, short_draft
from companion.core.spend import purpose
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.openloops.gate import Situation, Verdict, evaluate
from companion.features.openloops.logic import (
    PROMPT,
    SCHEMA,
    SYSTEM,
    LoopState,
    Making,
    OpenLoop,
    loop_labels,
    loop_note,
    loop_note_ref,
    normalise,
    parse,
    parse_resolved,
    pick_note,
    render_open_loops,
    to_loop,
    to_resolution,
)
from companion.features.openloops.store import ReachOut
from companion.loops.features import Feature, Offer, Offered, quiet
from companion.loops.record import Recorder
from companion.loops.turn import decide
from companion.prompts import get
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.loops.notes import Moment

log = logging.getLogger("companion.initiative")
SESSION = SessionId("initiative")
Draft = Callable[[OpenLoop], Awaitable[str]]
Log = Callable[[str, dict[str, Json]], None]


@dataclass(frozen=True, slots=True)
class LoopCounts:
    candidates: int = 0
    stored: int = 0
    rejected: int = 0
    cost_usd: float = 0.0
    resolved: int = 0


def _id() -> str:
    return uuid.uuid4().hex


async def extract_open_loops(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    window: Mapping[str, Utterance],
    targets: set[UtteranceId],
    when: tuple[datetime, tzinfo],
    note: Log,
) -> LoopCounts | None:
    """Record the open loops in the targeted messages, and close the ones they settle. None when
    the call itself failed, so the caller can keep the batch for another try."""
    now, tz = when
    labels = loop_labels(store.open_loops(rel))
    prompt = build_user_prompt(window, targets, {}, tz) + render_open_loops(labels)
    try:
        with purpose("loops"):
            result = await extractor.extract(SYSTEM, prompt, SCHEMA)
    except Exception:
        log.warning("open-loop extraction failed; the batch is kept for another try", exc_info=True)
        return None
    raw = parse(result.data)
    if raw is None:
        note("open loops: the answer was malformed and was ignored", {"model": result.model})
        return LoopCounts(cost_usd=result.cost_usd)
    known = {normalise(lp.claim) for lp in store.open_loops(rel)}
    made = Making(rel, now, tz, _id)
    stored = rejected = 0
    for item in raw:
        outcome = to_loop(item, window, made)
        if isinstance(outcome, str):
            rejected += 1
            note(f"open loop rejected: {outcome}", {"claim": item.claim, "quote": item.quote})
        elif normalise(outcome.claim) in known:
            rejected += 1
            note("open loop rejected: already recorded", {"claim": outcome.claim})
        else:
            store.add_open_loop(outcome)
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
    resolved = _close_resolved(store, result.data, labels, window, now, note)
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
    labels: Mapping[str, OpenLoop],
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
        store.open_loop_event(loop.id, LoopState.RESOLVED, f"they brought it up: {quote!r}", now)
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


HELD = "held, would otherwise reach out"  # the key of a reach-out the gate held back


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = _id()
    return Recorder(store, rel, SESSION, TurnId(trace), TraceId(trace), now)


def _situation(store: Store, rel: RelationshipId, now: datetime, tz: tzinfo) -> Situation:
    recent = store.history_before(rel, now, 8)
    sent = store.reach_outs(rel)
    today = [r for r in sent if r.at >= local_midnight(now)]
    theirs = [u.at for u in store.history_before(rel, now, 40) if u.speaker is Speaker.USER]
    last_theirs = max(theirs, default=None)
    unanswered = sum(
        1 for r in sent if r.mode == "live" and (last_theirs is None or r.at > last_theirs)
    )
    return Situation(
        now=now,
        tz=tz,
        last_message_at=recent[-1].at if recent else None,
        in_scene=scene_frame(recent, now) is not Frame.REAL,
        sent_today=len(today),
        last_reach_out_at=max((r.at for r in sent), default=None),
        unanswered=unanswered,
    )


async def tick(  # noqa: PLR0913, PLR0917
    store: Store,
    rel: RelationshipId,
    now: datetime,
    tz: tzinfo,
    draft: Draft | None,
    ticker: Ticker,
    caps: Caps = Caps(),  # noqa: B008
) -> Verdict:
    """One look at the open loops. In shadow mode a verdict to send is recorded with a drafted
    message and the loop is marked asked, but nothing is sent."""
    verdict = evaluate(store.open_loops(rel), _situation(store, rel, now, tz), caps)
    for lp in verdict.expired:
        store.open_loop_event(lp.id, LoopState.EXPIRED, "past its follow-up horizon", now)
        _record(store, rel, now).decide(
            "open loop expired", {"loop_id": lp.id}, reason=f"open loop expired: {lp.claim}"
        )
    if verdict.loop is None:
        log.debug("initiative: %s", verdict.reason)
        return verdict
    detail: dict[str, Json] = {"loop_id": verdict.loop.id, "claim": verdict.loop.claim}
    if not verdict.send:
        key = (verdict.loop.id, verdict.reason)
        if key not in ticker.seen:
            ticker.seen.add(key)
            reason = f"held, would otherwise reach out about {verdict.loop.claim}: {verdict.reason}"
            _record(store, rel, now).decide(
                HELD, detail, reason=reason, kind=DecisionKind.DO_NOTHING
            )
            log.info("initiative held: %s (%s)", verdict.loop.claim, verdict.reason)
        return verdict
    text = await draft(verdict.loop) if draft is not None else ""
    store.add_reach_out(ReachOut(_id(), rel, verdict.loop.id, "shadow", text, verdict.reason, now))
    store.open_loop_event(verdict.loop.id, LoopState.ASKED, "shadow reach-out, not sent", now)
    detail["draft"] = text
    _record(store, rel, now).decide(
        "shadow, would send",
        detail,
        reason=f"shadow, would send: {verdict.reason}",
        kind=DecisionKind.INITIATE,
    )
    log.info("initiative shadow: would send %r about %s", text, verdict.loop.claim)
    return verdict


DRAFT_PROMPT = get("system/openloops-draft")
DRAFT_SYSTEM = DRAFT_PROMPT.text
DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


def drafter(extractor: Extractor) -> Draft:
    """A function that drafts the check-in for a loop. Any failure gives an empty draft."""

    async def draft(loop: OpenLoop) -> str:
        prompt = f"They said: {loop.quote!r}\nThe thing: {loop.claim}\nKind: {loop.kind}"
        try:
            with purpose("initiative"):
                result = await extractor.extract(DRAFT_SYSTEM, prompt, DRAFT_SCHEMA)
        except Exception:
            log.warning("could not draft the check-in", exc_info=True)
            return ""
        message = result.data.get("message") if isinstance(result.data, dict) else None
        return short_draft(message) if isinstance(message, str) else ""

    return draft


MAX_TRIES = 3  # a batch that keeps failing is let go, so plans can never block on one


# A reader of its own messages in the same batch: the cost, or None when its call failed so the
# batch is read again. The slow loop passes the promise reader (J12) when it is on.
type OwnReader = Callable[
    [Store, Extractor, Mapping[str, Utterance], set[UtteranceId], tuple[datetime, tzinfo], Log],
    Awaitable[float | None],
]


@dataclass(frozen=True, slots=True)
class Reading:
    """Where the open-loop pass reads from: its batch size, the context before it, and how many
    batches one call may catch up."""

    batch: int
    context: int
    batches: int = 3
    promises: OwnReader | None = None  # also reads its own messages, for promises (J12, shadow)


async def catch_up_loops(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: Extractor,
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
        batch = store.utterances_after(rel, store.loop_cursor(rel), reading.batch)
        if not batch:
            break
        upto = (batch[-1].at, batch[-1].id)
        targets = {u.id for u in batch if u.speaker is Speaker.USER}
        mine = {u.id for u in batch if u.speaker is Speaker.COMPANION}
        own: set[UtteranceId] = mine if reading.promises is not None else set()
        if not targets and not own:
            store.record_loop_run(rel, upto, ok=True, reason="none of their messages", at=now)
            continue
        window = index_window([*store.history_before(rel, batch[0].at, reading.context), *batch])
        counts = (
            await extract_open_loops(store, extractor, rel, window, targets, when, note)
            if targets
            else LoopCounts()
        )
        spent = (
            await reading.promises(store, extractor, window, own, when, note)
            if own and reading.promises is not None
            else 0.0
        )
        if counts is not None and spent is not None:
            store.record_loop_run(rel, upto, ok=True, reason="read", at=now)
            total = _add(total, replace(counts, cost_usd=counts.cost_usd + spent))
            continue
        tries = store.loop_failed_tries(rel, upto[1]) + 1
        if tries >= MAX_TRIES:
            reason = f"open loops: gave up on a batch after {tries} failed tries"
            store.record_loop_run(rel, upto, ok=True, reason=reason, at=now)
            note(reason, {"messages": len(batch), "upto": upto[1]})
            continue
        store.record_loop_run(rel, upto, ok=False, reason=f"failed try {tries}", at=now)
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


LOOP_OFFERED = "open loop: offered as a note when they wrote"
LOOP_NOTE_EVERY = timedelta(hours=24)


def loop_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """Bring up one due open loop as a note when they write (J15): on a casual turn with no other
    nudge, at most one a day, each loop at most twice. Once the reply is stored the loop is marked
    asked, so it is never also a reach-out."""
    del found
    c, t = m.c, m.t
    if not quiet(m, so_far) or c.store.decided_since(c.rel, LOOP_OFFERED, t.now - LOOP_NOTE_EVERY):
        return Offer()
    offers = c.store.loop_events_with_reason(c.rel, LOOP_OFFERED)
    loop = pick_note(c.store.open_loops(c.rel), offers, t.now, local_zone())
    if loop is None:
        return Offer()
    detail: dict[str, Json] = {
        "loop_id": loop.id,
        "claim": loop.claim,
        "kind": loop.kind.value,
        "offer": offers.get(loop.id, 0) + 1,
        "note": loop_note_ref(loop),
    }

    def asked() -> None:
        c.store.open_loop_event(loop.id, LoopState.ASKED, LOOP_OFFERED, t.now)
        decide(c, t, LOOP_OFFERED, detail)

    note = loop_note(loop)
    return Offer((note,) if note else (), (asked,))


# Plans of theirs read in the open-loop batch; a due one is brought up as a note when they write.
OPENLOOPS = Feature("loop", note=loop_offer)
