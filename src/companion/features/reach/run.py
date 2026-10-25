"""The tick that reaches out for its own reasons (ADR 0021), in shadow: it learns their rhythm,
weighs every kind, asks the pure gate, and only then drafts. A would-send is recorded with its kind,
the one thing, the draft and the numbers, and nothing is sent: no code path here sends a message.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, tzinfo

from companion.core.crisis import reach_held
from companion.core.extractor import Extractor
from companion.core.frames import scene_frame
from companion.core.reachout import WOULD_NUDGE
from companion.core.rhythm import WINDOW, kept_hour, learn
from companion.core.types import (
    BeliefKind,
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    Subject,
    TraceId,
    TurnId,
)
from companion.features.reach.gate import Situation, answer, firsts, hold, pace, share
from companion.features.reach.logic import (
    DRAFT,
    DRAFT_SCHEMA,
    DROPPED,
    HELD,
    PACED,
    SENSITIVE,
    THING_REUSE,
    WOULD_SEND,
    Dial,
    Kind,
    Look,
    Pool,
    Thing,
    checked,
    choose,
    consider,
    draft_input,
    pick_thing,
    read_draft,
)
from companion.features.reach.store import Own
from companion.loops.ask import Judge, ask
from companion.loops.record import Recorder
from companion.loops.spendcap import over_cap
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.initiative")
SESSION = SessionId("initiative")
HISTORY = 5000  # messages read back, enough for two weeks
EPISODE_DAYS = timedelta(days=7)
DRAFT_JUDGE = Judge(
    "initiative", DRAFT, DRAFT_SCHEMA, read_draft, timeout=20.0, unread="no reach-out this time"
)


@dataclass(slots=True)
class Reacher:
    """The dial and the drafter, and what it already logged, so a hold or a lowered dial that
    lasts hours is one decision and not one per tick."""

    dial: Dial
    judge: Extractor | None
    cap: float | None = None  # the daily spend cap in dollars, None for none
    last_hold: tuple[str, str] | None = None
    paced: str | None = None


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = uuid.uuid4().hex
    return Recorder(store, rel, SESSION, TurnId(trace), TraceId(trace), now)


def _pool(store: Store, rel: RelationshipId, now: datetime) -> Pool:
    kinds = store.view_kinds(rel)
    keep = (BeliefKind.THREAD, BeliefKind.PREFERENCE)
    return Pool(
        memories=[
            (str(b.id), b.claim, b.sensitivity)
            for b in store.user_beliefs(rel)
            if b.subject is Subject.USER and b.kind in keep and b.frame is Frame.REAL
        ],
        tastes=[
            (str(b.id), b.claim)
            for b in store.self_beliefs(rel)
            if kinds.get(b.id) == "taste" and b.sensitivity < SENSITIVE
        ],
        episodes=[
            (e.id, e.gist)
            for e in store.episodes(rel)
            if e.kind == "everyday"
            and e.top_severity < SENSITIVE
            and now - e.end_at <= EPISODE_DAYS
        ],
    )


def _sent(store: Store, rel: RelationshipId, start: datetime) -> tuple[list[datetime], list[Own]]:
    """When it reached out (or would have, in shadow) in any way, and its own rows."""
    own = store.own_reach_outs(rel, start)
    nudges = [
        d.at
        for d in store.decisions_of_kind(rel, DecisionKind.INITIATE)
        if d.has_key(WOULD_NUDGE) and d.at >= start
    ]
    loops = [r.at for r in store.reach_outs(rel, start)]
    return sorted([*(r.at for r in own if r.mode != "dropped"), *nudges, *loops]), own


def _newest(own: list[Own], kind: Kind) -> datetime | None:
    return max((r.at for r in own if r.kind == kind and r.mode != "dropped"), default=None)


def situation(
    store: Store, rel: RelationshipId, when: tuple[datetime, tzinfo], reacher: Reacher
) -> tuple[Situation, Look]:
    """What the gate and the kinds are judged on, read from the store."""
    now, tz = when
    history = [u for u in store.history_before(rel, now, HISTORY) if now - u.at <= WINDOW]
    theirs = [(u.at, u.text) for u in history if u.speaker is Speaker.USER]
    times = [at for at, _ in theirs]
    rhythm = learn(times, now, tz)
    sent, own = _sent(store, rel, now - WINDOW)
    last_sent = max(sent, default=None)
    last_theirs = max(times, default=None)
    got = None if last_sent is None else answer(last_sent, theirs)
    events = [(u.at, u.speaker is Speaker.COMPANION) for u in history] + [(t, True) for t in sent]
    started = (
        got is not None
        and last_sent is not None
        and any(not mine and at > last_sent + got.after for at, mine in firsts(events, now))
    )
    attempts = [*sent, *(r.at for r in own if r.mode == "dropped")]
    used = frozenset(r.thing for r in own if r.thing and now - r.at <= THING_REUSE)
    seed = now.astimezone(tz).date().isoformat()
    sit = Situation(
        now=now,
        tz=tz,
        rhythm=rhythm,
        dial=reacher.dial,
        paced=pace(got, rhythm, started),
        last_message_at=history[-1].at if history else None,
        in_scene=scene_frame(history[-8:], now) is not Frame.REAL,
        last_own=max(attempts, default=None),
        unanswered=last_sent is not None and (last_theirs is None or last_theirs < last_sent),
        share=share(events, now),
        capped=over_cap(store, rel, reacher.cap, now) is not None,
        crisis=reach_held(lambda key, since: store.decided_since(rel, key, since), now),
    )
    look = Look(
        now=now,
        tz=tz,
        rhythm=rhythm,
        last_theirs=last_theirs,
        earlier=None,
        kept=kept_hour(times, now, tz),
        last_kept=_newest(own, Kind.KEPT),
        last_thought=_newest(own, Kind.THOUGHT),
        thing=pick_thing(_pool(store, rel, now), used, seed),
    )
    return sit, look


async def tick_reach(
    store: Store,
    rel: RelationshipId,
    when: tuple[datetime, tzinfo],
    reacher: Reacher,
    earlier: Kind | None = None,
) -> Own | None:
    """One look. `earlier` is a plan or a nudge the other ticks took this time; they come first.
    Returns the would-send it recorded, or None."""
    now = when[0]
    sit, base = situation(store, rel, when, reacher)
    considered = consider(replace(base, earlier=earlier))
    detail: dict[str, Json] = {**sit.detail(), "considered": [c.detail() for c in considered]}
    if sit.paced is not None and sit.paced != reacher.paced:
        _record(store, rel, now).decide(
            PACED, detail, reason=f"{PACED}: {sit.paced}; until they start a conversation"
        )
    reacher.paced = sit.paced
    pick = choose(considered)
    if pick is None or pick.kind in (Kind.PLAN, Kind.AWAY):
        why = "; ".join(f"{c.kind}: {c.why}" for c in considered)
        log.debug("reach: %s", why if pick is None else f"{pick.kind} went first")
        return None
    held = hold(sit)
    if held is not None:
        if reacher.last_hold != (pick.kind, held[0]):
            reacher.last_hold = (pick.kind, held[0])
            _record(store, rel, now).decide(
                HELD,
                {**detail, "kind": pick.kind.value, "hold": held[0].value},
                reason=f"{HELD}, would otherwise reach out ({pick.kind}): {held[1]}",
                kind=DecisionKind.DO_NOTHING,
            )
        log.debug("reach held (%s): %s", pick.kind, held[1])
        return None
    reacher.last_hold = None
    return await _draft(store, rel, now, reacher, (pick.kind, pick.why, base.thing, detail))


async def _draft(
    store: Store,
    rel: RelationshipId,
    now: datetime,
    reacher: Reacher,
    chosen: tuple[Kind, str, Thing | None, dict[str, Json]],
) -> Own | None:
    """The only paid call, made last: draft, check, record. A draft that fails the check is
    dropped, never rewritten, and recorded so it is not tried again for six hours."""
    kind, why, thing, detail = chosen
    got = (
        None
        if reacher.judge is None
        else await ask(reacher.judge, DRAFT_JUDGE, draft_input(kind, thing))
    )
    raw = got.value if got is not None else ""
    text, dropped = checked(raw) if got is not None else ("", "the draft call failed")
    about: Json = None if thing is None else {"source": thing.source, "text": thing.text}
    detail = {
        **detail,
        "kind": kind.value,
        "why": why,
        "thing": about,
        "drafted": raw,
        "prompt": DRAFT.ref,
    }
    row = Own(
        uuid.uuid4().hex,
        rel,
        kind.value,
        "" if thing is None else thing.id,
        text,
        "dropped" if dropped else "shadow",
        detail,
        now,
    )
    store.add_own_reach_out(row)
    if dropped:
        _record(store, rel, now).decide(
            DROPPED, detail, reason=f"{DROPPED} ({kind}): {dropped}", kind=DecisionKind.DO_NOTHING
        )
        log.info("reach: draft dropped (%s): %s", kind, dropped)
        return None
    _record(store, rel, now).decide(
        WOULD_SEND, detail, reason=f"{WOULD_SEND} ({kind}): {why}", kind=DecisionKind.INITIATE
    )
    log.info("reach shadow: would send %r (%s)", text, kind)
    return row
