"""The tick that reaches out for its own reasons (ADR 0021), in shadow: it learns their rhythm,
weighs every kind, asks the pure gate, and only then brainstorms a few messages, drops the ones that
break a rule, and lets a judge pick one or none. A would-send is recorded with its kind, every idea,
the pick and the numbers, and nothing is sent: no code path here sends a message.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, tzinfo

from companion.core.crisis import crisis_paused
from companion.core.extractor import StructuredModel
from companion.core.frames import scene_frame
from companion.core.reachout import WOULD_NUDGE, Held
from companion.core.rhythm import WINDOW, kept_hour, learn
from companion.core.types import (
    BeliefKind,
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Severity,
    Speaker,
    Subject,
    TraceId,
    TurnId,
    severity_from,
)
from companion.features.reach.gate import (
    AFTER_HEAVY,
    Situation,
    answer,
    firsts,
    hold,
    pace,
    share,
)
from companion.features.reach.logic import (
    DROPPED,
    HELD,
    IDEAS,
    IDEAS_SCHEMA,
    LINES,
    PACED,
    PICK,
    PICK_SCHEMA,
    SENSITIVE,
    THING_REUSE,
    WOULD_SEND,
    Context,
    Dial,
    Idea,
    Kind,
    Look,
    Pool,
    Thing,
    about_us,
    brief,
    choose,
    consider,
    pick_input,
    pick_thing,
    read_ideas,
    read_pick,
    screened,
)
from companion.features.reach.store import Own
from companion.kit.ask import Judge, ask
from companion.kit.record import Recorder
from companion.kit.spendcap import over_cap
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.initiative")
SESSION = SessionId("initiative")
HISTORY = 5000  # messages read back, enough for two weeks
EPISODE_DAYS = timedelta(days=7)
IDEAS_JUDGE = Judge(
    "initiative", IDEAS, IDEAS_SCHEMA, read_ideas, timeout=30.0, unread="no reach-out this time"
)
PICK_JUDGE = Judge(
    "initiative", PICK, PICK_SCHEMA, read_pick, timeout=20.0, unread="no reach-out this time"
)
HEAVY = Severity.SERIOUS  # a listening read at this severity or above is a heavy message


@dataclass(slots=True)
class Reacher:
    """The dial and the drafter, and what it already logged, so a hold or a lowered dial that
    lasts hours is one decision and not one per tick."""

    dial: Dial
    judge: StructuredModel | None
    cap: float | None = None  # the daily spend cap in dollars, None for none
    last_hold: tuple[str, str] | None = None
    paced: str | None = None


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = uuid.uuid4().hex
    return Recorder(store, rel, SESSION, TurnId(trace), TraceId(trace), now)


def _pool(store: Store, rel: RelationshipId, now: datetime) -> Pool:
    """What a thought could be about. Never a memory the scene lane placed as intimate (ADR 0026):
    some are stored at a low sensitivity, and one was picked for a weekday morning (2026-11-03)."""
    kinds = store.view_kinds(rel)
    keep = (BeliefKind.THREAD, BeliefKind.PREFERENCE)
    intimate = store.intimate_memory().intimate(rel)
    return Pool(
        memories=[
            (str(b.id), b.claim, b.sensitivity)
            for b in store.user_beliefs(rel)
            if b.subject is Subject.USER
            and b.kind in keep
            and b.frame is Frame.REAL
            and b.id not in intimate
        ],
        tastes=[
            (str(b.id), b.claim)
            for b in store.self_beliefs(rel)
            if kinds.get(b.id) == "taste" and b.sensitivity < SENSITIVE
        ],
        episodes=[
            (e.id, e.gist)
            for e in store.episodes(rel)
            if e.kind == "everyday" and e.top_severity < HEAVY and now - e.end_at <= EPISODE_DAYS
        ],
    )


def _sent(store: Store, rel: RelationshipId, start: datetime) -> tuple[list[datetime], list[Own]]:
    """When it reached out (or would have, in shadow) in any way, and its own rows."""
    own = store.own_reach_outs(rel, start)
    nudges = [d.at for d in store.decisions_with_key(rel, WOULD_NUDGE, start)]
    loops = [r.at for r in store.reach_outs(rel, start)]
    return sorted([*(r.at for r in own if r.mode != "dropped"), *nudges, *loops]), own


def _heavy_at(store: Store, rel: RelationshipId, now: datetime) -> datetime | None:
    """Their newest message the listening read found heavy, in the window the gate holds for."""
    found = [
        d.at
        for d in store.decisions_with_key(rel, "listening", now - AFTER_HEAVY)
        if isinstance(labels := (d.detail or {}).get("labels"), dict)
        and (sev := severity_from(labels.get("severity"))) is not None
        and sev >= HEAVY
        and d.at <= now
    ]
    return max(found, default=None)


def _kept_out(store: Store, rel: RelationshipId, since: datetime, now: datetime) -> bool:
    """Whether the listening read found any of their messages since `since` intimate or heavy. The
    last lines are shown only when they are plain everyday talk: an intimate episode is not always
    a pretend frame, and lines skipping a scene reached back to a heavy disclosure (2026-11-03)."""
    return any(
        isinstance(labels := (d.detail or {}).get("labels"), dict)
        and (
            labels.get("intimate") is True
            or ((sev := severity_from(labels.get("severity"))) is not None and sev >= HEAVY)
        )
        for d in store.decisions_with_key(rel, "listening", since)
        if d.at <= now
    )


def context(
    store: Store,
    rel: RelationshipId,
    when: tuple[datetime, tzinfo],
    kind: Kind,
    thing: Thing | None,
) -> Context:
    """What the brainstorm and the pick see, read from the store as it was at `when`."""
    now, tz = when
    said = store.history_before(rel, now, LINES)
    if said and (
        any(u.frame is not Frame.REAL for u in said) or _kept_out(store, rel, said[0].at, now)
    ):
        said = []
    keep = (BeliefKind.THREAD, BeliefKind.PREFERENCE, BeliefKind.TRAIT)
    intimate = store.intimate_memory().intimate(rel)
    theirs = sorted(
        (
            b
            for b in store.user_beliefs_as_of(rel, now)
            if b.subject is Subject.USER
            and b.kind in keep
            and b.frame is Frame.REAL
            and b.sensitivity < SENSITIVE
            and b.id not in intimate
        ),
        key=lambda b: b.valid_from,
        reverse=True,
    )
    pool = _pool(store, rel, now)
    own = store.own_reach_outs(rel, now - WINDOW)
    return Context(
        local=now.astimezone(tz),
        kind=kind,
        thing=thing,
        lines=[("them" if u.speaker is Speaker.USER else "you", u.text) for u in said],
        gists=[g for _, g in pool.episodes],
        memories=[b.claim for b in theirs],
        tastes=[c for _, c in pool.tastes if not about_us(c)],
        sent=[r.draft for r in own if r.mode != "dropped" and r.at <= now],
    )


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
        crisis=crisis_paused(lambda key, since: store.decided_since(rel, key, since), now),
        heavy_at=_heavy_at(store, rel, now),
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


def holds(
    store: Store, rel: RelationshipId, when: tuple[datetime, tzinfo], reacher: Reacher
) -> Held | None:
    """The shared gate's answer for any reach-out now (ADR 0023), asked by the daemon for a plan of
    theirs too: what holds it and why, or None."""
    held = hold(situation(store, rel, when, reacher)[0])
    return None if held is None else Held(held[0].value, held[1])


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
    return await _draft(store, rel, when, reacher, (pick.kind, pick.why, base.thing, detail))


async def ideas(judge: StructuredModel, c: Context) -> tuple[Idea | None, dict[str, Json]]:
    """Brainstorm, drop what breaks a rule, and let the judge pick one or none. The picked idea, and
    what happened at each step for the record."""
    got = await ask(judge, IDEAS_JUDGE, brief(c))
    if got is None:
        return None, {"dropped": "the brainstorm call failed"}
    kept, out = screened(got.value)
    step: dict[str, Json] = {
        "ideas": [{"angle": i.angle, "message": i.message, "about": i.about} for i in got.value],
        "screened_out": [{"message": i.message, "why": why} for i, why in out],
        "prompts": [IDEAS.ref, PICK.ref],
    }
    if not kept:
        return None, {**step, "dropped": "no idea passed the checks"}
    picked = await ask(judge, PICK_JUDGE, pick_input(c, kept))
    if picked is None:
        return None, {**step, "dropped": "the pick call failed"}
    n, why = picked.value
    step = {**step, "pick": n, "pick_why": why}
    if not 1 <= n <= len(kept):
        return None, {**step, "dropped": f"the judge sent none: {why}"}
    return kept[n - 1], step


async def _draft(
    store: Store,
    rel: RelationshipId,
    when: tuple[datetime, tzinfo],
    reacher: Reacher,
    chosen: tuple[Kind, str, Thing | None, dict[str, Json]],
) -> Own | None:
    """The only paid calls, made last: brainstorm, screen, pick, record. When nothing is picked, it
    is recorded as dropped, so it is not tried again for six hours."""
    now = when[0]
    kind, why, thing, detail = chosen
    if reacher.judge is None:
        idea, step = None, {"dropped": "no model"}
    else:
        idea, step = await ideas(reacher.judge, context(store, rel, when, kind, thing))
    about: Json = None if thing is None else {"source": thing.source, "text": thing.text}
    detail = {**detail, "kind": kind.value, "why": why, "thing": about, **step}
    dropped = step.get("dropped")
    row = Own(
        uuid.uuid4().hex,
        rel,
        kind.value,
        "" if thing is None else thing.id,
        "" if idea is None else idea.message,
        "dropped" if idea is None else "shadow",
        detail,
        now,
    )
    store.add_own_reach_out(row)
    if idea is None:
        _record(store, rel, now).decide(
            DROPPED, detail, reason=f"{DROPPED} ({kind}): {dropped}", kind=DecisionKind.DO_NOTHING
        )
        log.info("reach: nothing sent (%s): %s", kind, dropped)
        return None
    _record(store, rel, now).decide(
        WOULD_SEND, detail, reason=f"{WOULD_SEND} ({kind}): {why}", kind=DecisionKind.INITIATE
    )
    log.info("reach shadow: would send %r (%s, %s)", idea.message, kind, idea.angle)
    return row
