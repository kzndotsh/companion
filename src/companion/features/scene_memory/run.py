"""The intimate scene lane (ADR 0026), in shadow by default. After a memory pass: place each memory
about them in a lane, read three times, and note how they play from the scenes that ended. On a
turn the roleplay talker answers: build the scene card (limits, the entries nearest the moment,
perhaps one curious item, the basics) and log it; `on` sends it instead of the everyday card, and
leaves intimate memories off every other turn's card. A failed read leaves the batch or the scene
for the next pass."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.frames import is_assertable
from companion.core.spend import purpose
from companion.core.turn.address import names_them
from companion.core.turn.floor import BRUSH_KEY
from companion.core.types import (
    Belief,
    BeliefId,
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
from companion.core.vectors import Vector, dot
from companion.features.scene_memory.logic import (
    BATCH,
    COOL,
    LANE,
    LANE_SCHEMA,
    LIMIT_CHECK,
    LIMIT_SCHEMA,
    LIMITS,
    PATTERN,
    PATTERN_SCHEMA,
    WHY_TEXT,
    BrushRead,
    Entry,
    Excluded,
    Facts,
    Intimate,
    Offered,
    Pattern,
    Place,
    Quote,
    Scene,
    SceneCard,
    Stance,
    Why,
    agree,
    closed,
    cooled,
    lane_prompt,
    limit_prompt,
    parse_lanes,
    parse_limit,
    parse_patterns,
    pattern_entry,
    pattern_prompt,
    refuse,
    render_scene,
    scene_card,
    scenes,
    screen,
)
from companion.features.scene_memory.store import By
from companion.loops.current import Heard, Turn, decide
from companion.loops.features import Feature
from companion.loops.reads import read_times
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.core.card import Card
    from companion.core.vectors import Embedder
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.scene")

SESSION = SessionId("scene memory")
READ = 400  # messages read past the bookmark per pass
SCENES = 3  # ended scenes read per pass
LOOK_SECONDS = 2.0

PLACED = "scene memory: a memory placed"
NOTED = "scene memory: a pattern noted"
DROPPED = "scene memory: a pattern dropped"
UNREAD = "scene memory: a scene left unread by the floor"
CARD = "scene memory: the scene card"
LEFT_OFF = "scene memory: intimate memories left off the everyday card"
OFFERED = "scene memory: a curious item offered"


@dataclass(frozen=True, slots=True)
class Spent:
    cost_usd: float = 0.0


def _pass_recorder(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    run = uuid.uuid4().hex
    return Recorder(store, rel, SESSION, TurnId(run), TraceId(run), now)


def facts_of(b: Belief, held: frozenset[UtteranceId], heavy: frozenset[UtteranceId]) -> Facts:
    ids = {e.utterance_id for e in b.evidence}
    return Facts(held=bool(ids & held), heavy=bool(ids & heavy))


def _placed_detail(bid: BeliefId, p: Place) -> tuple[dict[str, Json], str] | None:
    """The decision for a memory placed in or kept out of the intimate lane; None for everyday."""
    if isinstance(p, Intimate):
        return {"belief": bid, "lane": "intimate", "stance": p.stance.value}, (
            f"scene memory: intimate, {p.stance.value}"
        )
    if isinstance(p, Excluded):
        return {"belief": bid, "lane": "excluded", "why": p.why.value}, (
            f"scene memory: kept out of scenes, {WHY_TEXT[p.why]}"
        )
    return None


async def label_lanes(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
) -> Spent:
    """Place one batch of memories that have no lane yet, each read three times. A failed read
    places nothing: the batch waits for the next pass, never placed from fewer reads."""
    sm = store.scene_memory()
    have = sm.places(rel)
    again = sm.doubted_before(rel, LANE.ref)  # a doubt under an older prompt is read again once
    todo = [
        b
        for b in store.user_beliefs(rel)
        if is_assertable(b) and (b.id not in have or b.id in again)
    ][:BATCH]
    if not todo:
        return Spent()
    text, refs = lane_prompt(todo)
    got = await read_times(
        extractor,
        LANE.text,
        text,
        LANE_SCHEMA,
        lambda data: parse_lanes(data, refs),
        spend="scene memory",
    )
    if got.failed:
        log.warning("scene lanes: a read failed; the batch waits for the next pass")
        return Spent(got.cost_usd)
    agreed = agree([v for v in got.values if v is not None], refs.values())
    held, heavy = sm.facts(rel, [e.utterance_id for b in todo for e in b.evidence])
    places = {b.id: screen(agreed[b.id], b, facts_of(b, held, heavy)) for b in todo}
    spent = got.cost_usd
    for b in todo:
        place = places[b.id]
        if isinstance(place, Intimate) and place.stance in LIMITS:
            sure, cost = await _a_limit(extractor, b)
            spent += cost
            if not sure:
                places[b.id] = Excluded(Why.DOUBT)
    sm.place(places, By(got.model, LANE.ref, now))
    record = _pass_recorder(store, rel, now)
    for bid, p in places.items():
        logged = _placed_detail(bid, p)
        if logged is not None:
            record.decide(PLACED, logged[0] | {"prompt": LANE.ref}, reason=logged[1])
    return Spent(spent)


async def _a_limit(extractor: StructuredModel, b: Belief) -> tuple[bool, float]:
    """Whether their own words set the limit the lane reads gave: every read must say so."""
    got = await read_times(
        extractor,
        LIMIT_CHECK.text,
        limit_prompt(b),
        LIMIT_SCHEMA,
        parse_limit,
        spend="scene memory",
    )
    sure = not got.failed and all(v is True for v in got.values)
    return sure, got.cost_usd


def _span(batch: Sequence[Utterance], before: Utterance | None) -> Utterance | None:
    """The last message of the batch before `before` (all of it when None)."""
    if before is None:
        return batch[-1]
    i = batch.index(before)
    return batch[i - 1] if i > 0 else None


async def read_scenes(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
) -> Spent:
    """Note how they play from the scenes that ended past the bookmark, oldest first, up to SCENES a
    pass. The bookmark moves to just before the first scene left for later."""
    sm = store.scene_memory()
    batch = store.utterances_after(rel, sm.cursor(rel), READ)
    if not batch:
        return Spent()
    found = scenes(batch)
    full = len(batch) == READ
    cost = 0.0
    waiting: Utterance | None = None
    for n, scene in enumerate(found):
        ended_here = closed(scene, batch, scene.messages[-1].at)  # a message out of play follows
        cut = full and scene is found[-1] and scene.messages[0] is not batch[0] and not ended_here
        if n >= SCENES or cut or not closed(scene, batch, now):
            waiting = scene.messages[0]
            break
        spent = await _read_scene(store, extractor, rel, scene, now)
        if spent is None:
            waiting = scene.messages[0]
            break
        cost += spent
    upto = _span(batch, waiting)
    if upto is not None:
        sm.read_upto(rel, (upto.at, upto.id), now)
    return Spent(cost)


async def _read_scene(
    store: Store, extractor: StructuredModel, rel: RelationshipId, scene: Scene, now: datetime
) -> float | None:
    """Read one ended scene for patterns: their cost, or None when the read failed. A scene with a
    turn the minor check held is never read."""
    sm = store.scene_memory()
    theirs = [u.id for u in scene.messages if u.speaker is Speaker.USER]
    held, _ = sm.facts(rel, theirs)
    record = _pass_recorder(store, rel, now)
    if held:
        record.decide(UNREAD, {"scene": scene.key, "messages": len(scene.messages)})
        return 0.0
    known = [p for p in sm.patterns(rel) if not p.retired]
    text, labels, refs = pattern_prompt([(p.id, p.claim) for p in known], scene)
    try:
        with purpose("scene memory"):
            got = await extractor.extract(PATTERN.text, text, PATTERN_SCHEMA)
    except Exception as err:
        log.warning("scene patterns: the read failed; the scene is read again next pass: %r", err)
        return None
    proposed = parse_patterns(got.data)
    if proposed is None:
        log.warning("scene patterns: the answer was unreadable; read again next pass")
        return None
    by_id = {p.id: p for p in known}
    by = By(got.model, PATTERN.ref, now)
    for p in proposed:
        why = refuse(p, labels)
        if why is not None:
            floor = why == WHY_TEXT[Why.FLOOR]
            detail: dict[str, Json] = {"scene": scene.key, "why": why}
            if not floor:
                detail |= {"claim": p.claim, "stance": p.stance}
            record.decide(DROPPED, detail, reason=f"{DROPPED}: {why}")
            continue
        quote = Quote(scene.key, labels[p.message.strip("[] ")].id, p.quote)
        seen = by_id.get(refs.get(p.pattern.strip("[] "), ""))
        if seen is not None and any(q.scene == scene.key for q in seen.quotes):
            continue
        if seen is not None:
            sm.add_quote(seen.id, quote, now)
            pid, claim, scenes_seen = seen.id, seen.claim, seen.scenes + 1
        else:
            made = Pattern(uuid.uuid4().hex, p.claim, Stance(p.stance), (quote,))
            sm.add_pattern(rel, made, by)
            by_id[made.id] = made
            pid, claim, scenes_seen = made.id, made.claim, 1
        record.decide(
            NOTED,
            {"pattern": pid, "claim": claim, "scene": scene.key, "scenes": scenes_seen},
            reason=f"{NOTED}: seen in {scenes_seen} scene(s)",
        )
    return got.cost_usd


type Step = Callable[[Store, StructuredModel, RelationshipId, datetime], Awaitable[Spent]]


def pass_step(mode: str) -> Step | None:
    """The step the memory pass runs for `COMPANION_SCENE_MEMORY`, or None when it is off."""
    if mode == "off":
        return None

    async def step(
        store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
    ) -> Spent:
        placed = await label_lanes(store, extractor, rel, now)
        read = await read_scenes(store, extractor, rel, now)
        return Spent(placed.cost_usd + read.cost_usd)

    return step


def entries(store: Store, rel: RelationshipId) -> tuple[Entry, ...]:
    """What a scene card may show: the memories placed intimate that still pass the floor, and the
    patterns seen in enough scenes. The floor is read again here, over every turn they came from."""
    sm = store.scene_memory()
    places = sm.places(rel)
    beliefs = [
        b
        for b in store.user_beliefs(rel)
        if is_assertable(b) and isinstance(places.get(b.id), Intimate)
    ]
    patterns = [p for p in sm.patterns(rel) if not p.retired]
    said = [e.utterance_id for b in beliefs for e in b.evidence]
    held, heavy = sm.facts(rel, [*said, *(q.utterance for p in patterns for q in p.quotes)])
    out: list[Entry] = []
    for b in beliefs:
        p = screen(places[b.id], b, facts_of(b, held, heavy))
        if isinstance(p, Intimate):
            out.append(Entry(b.id, b.claim, p.stance, tuple(e.quote for e in b.evidence)))
    out += [e for p in patterns if (e := pattern_entry(p, held)) is not None]
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Scored:
    """What the look-up found: the entries and how near each is to the moment."""

    entries: tuple[Entry, ...]
    scores: dict[str, float]


async def _vectors(
    c: Conversation, embedder: Embedder, found: Sequence[Entry], said: str, now: datetime
) -> tuple[Vector, dict[str, Vector]] | None:
    """The moment's vector and every entry's, embedding the missing ones in the same call."""
    store, model, sm = c.store, c.embed_model, c.store.scene_memory()
    have: dict[str, Vector] = {**store.belief_embeddings(c.rel, model), **sm.vectors(c.rel, model)}
    missing = [e for e in found if e.id not in have]
    try:
        with purpose("scene memory"):
            got = await asyncio.wait_for(
                embedder.embed([said, *(e.claim for e in missing)]), LOOK_SECONDS
            )
    except Exception as err:
        log.warning("scene look-up failed or was slow; nearest left out: %r", err)
        return None
    fresh = dict(zip((e.id for e in missing), got.vectors[1:], strict=True))
    patterns = {e.id: fresh[e.id] for e in missing if e.pattern}
    if patterns:
        sm.add_vectors(patterns, model, now)
    told = {BeliefId(e.id): fresh[e.id] for e in missing if not e.pattern}
    if told:
        store.add_belief_embeddings(c.rel, told, model, now)
    return got.vectors[0], {**have, **fresh}


async def nearest_for_turn(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> Scored | None:
    """On a turn that may be a scene (a pretend scene in progress, or intimate talk the operator
    lets the roleplay talker answer), how near each entry is to the moment: their message with the
    reply before it."""
    intimate = c.route_intimate and heard is not None and heard[0].intimate
    if c.scene_memory == "off" or c.embedder is None or c.roleplay_talker is None:
        return None
    if in_scene is not Frame.PLAY and not intimate:
        return None
    found = entries(c.store, c.rel)
    if not found:
        return Scored((), {})
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    moment = f"{replies[-1]}\n{t.text}" if replies else t.text
    got = await _vectors(c, c.embedder, found, moment, t.now)
    if got is None:
        return None
    query, vectors = got
    return Scored(found, {e.id: dot(query, vectors[e.id]) for e in found if e.id in vectors})


@dataclass(frozen=True, slots=True)
class SceneLane:
    """What the scene lane does to this turn's request."""

    hidden: frozenset[BeliefId] = frozenset()  # left off the everyday card
    text: str | None = None  # sent instead of the everyday card
    after: tuple[Callable[[], None], ...] = ()  # the offer's log, once the turn is stored


def _may_offer(c: Conversation, t: Turn) -> bool:
    """Only when this turn's brush-off read answered, and answered no."""
    return any(
        d.has_key(BRUSH_KEY)
        and isinstance(d.detail, dict)
        and d.detail.get("declines") is False
        and "scorer" in d.detail
        for d in c.store.decisions_for_turn(c.rel, t.turn)
    )


def _cooled(c: Conversation, t: Turn) -> frozenset[str]:
    since = t.now - COOL
    offers = [
        Offered(d.at, d.turn_id, str(d.detail["entry"]))
        for d in c.store.decisions_with_key(c.rel, OFFERED, since)
        if isinstance(d.detail, dict) and "entry" in d.detail
    ]
    reads = [
        BrushRead(d.at, d.turn_id, isinstance(d.detail, dict) and d.detail.get("declines") is True)
        for d in c.store.decisions_with_key(c.rel, BRUSH_KEY, since)
    ]
    return cooled(offers, reads, t.now)


def _card_detail(card: SceneCard, text: str, *, sent: bool, scored: bool) -> dict[str, Json]:
    return {
        "limits": [e.id for e in card.limits],
        "nearest": [{"id": e.id, "score": round(s, 3)} for e, s in card.nearest],
        "offer": card.offer.id if card.offer is not None else None,
        "basics": len(card.basics),
        "scored": scored,
        "sent": sent,
        "text": text,
    }


def scene_lane(
    c: Conversation,
    t: Turn,
    found: object,
    *,
    roleplay: bool,
    card: Card,
) -> SceneLane:
    """On a turn the roleplay talker answers: the scene card, logged, and sent when on. On any other
    turn: the intimate memories the everyday card holds, logged, and left off when on."""
    if c.scene_memory == "off":
        return SceneLane()
    live = c.scene_memory == "on"
    if not roleplay:
        hidden = c.store.scene_memory().intimate(c.rel)
        on_card = hidden & {b.id for b in (*card.usable, *card.held, *card.older)}
        if on_card:
            decide(
                c,
                t,
                LEFT_OFF,
                {"beliefs": [str(b) for b in sorted(on_card)], "sent": not live},
                reason=f"{LEFT_OFF}: {len(on_card)}" + ("" if live else " (shadow: still sent)"),
            )
        return SceneLane(hidden=hidden if live else frozenset())
    scored = found if isinstance(found, Scored) else None
    may = _may_offer(c, t)
    made = scene_card(
        scored.entries if scored is not None else entries(c.store, c.rel),
        scored.scores if scored is not None else {},
        [b.claim for b in c.store.user_beliefs(c.rel) if is_assertable(b) and names_them(b)],
        may_offer=may,
        cooled=_cooled(c, t) if may else (),
    )
    text = render_scene(made)
    decide(
        c,
        t,
        CARD,
        _card_detail(made, text, sent=live, scored=scored is not None),
        reason=f"{CARD}: {len(made.limits)} limits, {len(made.nearest)} nearest,"
        f" {'one curious item it may offer' if made.offer else 'no offer'},"
        f" {len(made.basics)} basics" + ("" if live else " (shadow: not sent)"),
    )
    offer = made.offer
    if not live or offer is None:
        return SceneLane(text=text if live else None)
    return SceneLane(text=text, after=(lambda: decide(c, t, OFFERED, {"entry": offer.id}),))


SCENE = Feature("scene", look=nearest_for_turn)
