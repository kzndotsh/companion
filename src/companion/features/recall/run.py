"""Recall's two triggers before the reply, each a look-up and a note: asked (they ask it to
remember) and near (the relevance look-up, ADR 0018, also run in shadow beside the turn). A failed
or slow look-up only means nothing is added; the reply goes out as it would have."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from companion.core import switch
from companion.core.card import Card
from companion.core.extractor import StructuredModel
from companion.core.recall import PROMPT as RECALL_PROMPT
from companion.core.recall import RECENT, recall_note
from companion.core.spend import purpose
from companion.core.switch import Mode
from companion.core.types import Belief, BeliefId, Frame, Json, RelationshipId, Severity, Speaker
from companion.core.vectors import Embedder, nearest
from companion.features.intimate.store import IntimateMemory
from companion.features.recall.logic import GATE as RELEVANCE_GATE
from companion.features.recall.logic import LIVE as RELEVANCE_LIVE
from companion.features.recall.logic import PROMPT, SCHEMA, build_prompt, eligible, extras, parse
from companion.features.recall.logic import SHADOW as RELEVANCE_SHADOW
from companion.kit.ask import Judge, ask, whole_answer
from companion.kit.current import Heard, Turn, decide, mark
from companion.kit.embed import bounded, embed_missing
from companion.kit.features import Feature, Offer, Offered
from companion.kit.recall import Context, Recalled
from companion.kit.recall import look_up as recall_look_up
from companion.prompts import get
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.relevance")
TIMEOUT_SECONDS = 10.0
# Only the memories offered can be picked, so `look_up` finishes the reading.
PICKER = Judge(
    "relevance",
    PROMPT,
    SCHEMA,
    whole_answer,
    timeout=TIMEOUT_SECONDS,
    unread="no memories picked this turn; the nearest are still logged",
)
LOGGED_NEAREST = 3  # nearest memories written to the decision, for reading the look-up later


@dataclass(frozen=True, slots=True)
class Lookup:
    """What one shadow look-up found, for the decision detail."""

    detail: dict[str, Json]


def _row(b: Belief, on_card: set[BeliefId], score: float | None = None) -> dict[str, Json]:
    row: dict[str, Json] = {"id": b.id, "claim": b.claim, "on_card": b.id in on_card}
    if score is not None:
        row["score"] = round(score, 3)
    return row


async def look_up(  # noqa: PLR0913
    store: Store,
    embedder: Embedder,
    judge: StructuredModel,
    rel: RelationshipId,
    *,
    model: str,
    said: str,
    last_reply: str | None,
    sharing: bool,
    on_card: set[BeliefId],
    now: datetime,
    gate: float | None = None,
    hidden: frozenset[BeliefId] = frozenset(),
) -> Lookup:
    """With `gate`, the small model is asked only when the closest memory scores at least that.
    `hidden` memories are never searched (the intimate lane outside a scene, ADR 0026)."""
    started = time.perf_counter()
    cost = await embed_missing(store, embedder, rel, model, now)
    texts = [said, f"{last_reply}\n{said}"] if last_reply else [said]
    with purpose("relevance"):
        query = await embedder.embed(texts)
    embed_ms = int((time.perf_counter() - started) * 1000)
    cost += query.cost_usd
    pool = eligible(store.user_beliefs(rel), asked=False, sharing=sharing, hidden=hidden)
    vectors = store.belief_embeddings(rel, model)
    alone = nearest(query.vectors[0], pool, vectors)
    shortlist = nearest(
        query.vectors[-1], pool, vectors
    )  # with their last reply, when there is one
    started = time.perf_counter()
    gated = gate is not None and (not shortlist or shortlist[0][1] < gate)
    picked: list[Belief] = []
    pick_failed = False
    pick_cost, pick_model = 0.0, ""
    if not gated:
        offered = [b for b, _ in shortlist]
        got = await ask(judge, PICKER, build_prompt(last_reply, said, offered))
        pick_failed = got is None
        if got is not None:
            picked = parse(got.value, offered)
            pick_cost, pick_model = got.cost_usd, got.model
    detail: dict[str, Json] = {
        "nearest": [_row(b, on_card, s) for b, s in alone[:LOGGED_NEAREST]],
        "nearest_in_context": [_row(b, on_card, s) for b, s in shortlist[:LOGGED_NEAREST]],
        "picked": [_row(b, on_card) for b in picked],
        "searched": len(pool),
        "embed_ms": embed_ms,
        "pick_ms": int((time.perf_counter() - started) * 1000),
        "cost_usd": round(cost + pick_cost, 6),
        "prompt": PROMPT.ref,
        "embed_model": model,
        "pick_model": pick_model,
        "gated": gated,
        "pick_failed": pick_failed,  # the picker was asked and gave nothing usable
    }
    log.debug(
        "relevance: %d picked of %d nearest (%d searched), on card %d, %dms + %dms, $%.5f",
        len(picked),
        len(shortlist),
        len(pool),
        sum(b.id in on_card for b in picked),
        detail["embed_ms"],
        detail["pick_ms"],
        cost + pick_cost,
    )
    return Lookup(detail)


async def shadow(  # noqa: PLR0913
    store: Store,
    embedder: Embedder,
    judge: StructuredModel,
    rel: RelationshipId,
    *,
    model: str,
    said: str,
    last_reply: str | None,
    sharing: bool,
    on_card: Sequence[BeliefId],
    now: datetime,
    gate: float | None = None,
    timeout: float = TIMEOUT_SECONDS,
    hidden: frozenset[BeliefId] = frozenset(),
) -> Lookup | None:
    """The look-up with a time limit; None when it failed or ran out of time."""
    return await bounded(
        look_up(
            store,
            embedder,
            judge,
            rel,
            model=model,
            said=said,
            last_reply=last_reply,
            sharing=sharing,
            on_card=set(on_card),
            now=now,
            gate=gate,
            hidden=hidden,
        ),
        deadline=timeout,
        what="relevance look-up",
        unread="nothing is added",
    )


def _hidden(c: Runtime) -> frozenset[BeliefId]:
    """The intimate lane, left out of the look-up when the scene memory is on (ADR 0026)."""
    return (
        c.store.part(IntimateMemory).intimate(c.rel)
        if c.mode(switch.INTIMATE_MEMORY) is Mode.ON
        else frozenset()
    )


RELEVANT_NOTE = get("notes/relevant")
LIVE_SECONDS = 3.0  # a slow look-up only means no memories are offered this turn


async def relevant_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[tuple[BeliefId, str], ...]:
    """With the look-up on (ADR 0018): the memories a small model picks as bearing on their message,
    asked only when the closest memory is near (GATE), outside a scene. Logged either way. With no
    listening read because the judge failed it still runs, as a turn that is not sharing, so nothing
    held is offered; with listening switched off it does not run, as before."""
    if c.mode(switch.RELEVANCE) is not Mode.ON or c.embedder is None or c.judge is None:
        return ()
    if heard is None and not c.on(switch.LISTEN):
        return ()
    if in_scene is not Frame.REAL:
        return ()
    mark(t, "relevance look-up")
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    found = await shadow(
        c.store,
        c.embedder,
        c.judge,
        c.rel,
        model=c.embed_model,
        said=t.text,
        last_reply=replies[-1] if replies else None,
        sharing=heard is not None and heard[0].severity >= Severity.EVERYDAY,
        on_card=(),
        now=t.now,
        gate=RELEVANCE_GATE,
        timeout=LIVE_SECONDS,
        hidden=_hidden(c),
    )
    if found is None:
        return ()
    decide(c, t, RELEVANCE_LIVE, found.detail)
    rows = found.detail.get("picked")
    return tuple(
        (BeliefId(str(row["id"])), str(row["claim"]))
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and isinstance(row.get("claim"), str) and "id" in row
    )


def relevant_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    del so_far
    picked = cast("tuple[tuple[BeliefId, str], ...]", found or ())
    recalled = m.looked.find(Recalled)
    shown = [b.id for b in recalled.picked] if recalled is not None else []
    picks = extras(picked, on_card=m.on_card, recalled=shown)
    if not picks:
        return Offer()
    return Offer((RELEVANT_NOTE.render(items="\n".join(f"- {p}" for p in picks)),))


async def shadow_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """With the look-up in shadow: what it would have kept in mind on an ordinary message, logged
    beside the turn; it never holds up or changes the reply."""
    if (
        c.mode(switch.RELEVANCE) is not Mode.SHADOW
        or c.embedder is None
        or c.judge is None
        or (heard is None and not c.on(switch.LISTEN))
        or in_scene is not Frame.REAL
    ):
        return
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    found = await shadow(
        c.store,
        c.embedder,
        c.judge,
        c.rel,
        model=c.embed_model,
        said=t.text,
        last_reply=replies[-1] if replies else None,
        sharing=heard is not None and heard[0].severity >= Severity.EVERYDAY,
        on_card=[b.id for b in (*card.usable, *card.guarded, *card.older)],
        now=t.now,
        hidden=_hidden(c),
    )
    if found is not None:
        decide(c, t, RELEVANCE_SHADOW, found.detail)


async def recall_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> Recalled | None:
    """When they asked it to remember something, look it up across what they may be asked about,
    and log it. In a scene `heard` is the route's read (`scene_read`), since listening does not run
    there."""
    del in_scene
    if c.judge is None or heard is None or not heard[0].recall or not heard[0].topic:
        return None
    topic = heard[0].topic
    mark(t, f"recall look-up: {topic!r}")
    said = [f"{'they' if u.speaker is Speaker.USER else 'you'}: {u.text}" for u in t.prior]
    pool = eligible(c.store.user_beliefs(c.rel), asked=True, sharing=True, hidden=_hidden(c))
    recalled = await recall_look_up(
        c.judge,
        pool,
        topic,
        Context(c.store.last_support(c.rel), t.now, [*said[-(RECENT - 1) :], f"they: {t.text}"]),
    )
    found = recalled.picked if recalled is not None else ()
    reason = f"recall: they asked about {topic!r}; " + (
        f"{len(found)} found" if recalled is not None else "the look-up failed"
    )
    decide(
        c,
        t,
        "recall",
        {
            "topic": topic,
            "picked": [b.id for b in found],
            "searched": recalled.searched if recalled is not None else 0,
            "scorer": recalled.model if recalled is not None else "",
            "prompt": RECALL_PROMPT.ref,
        },
        reason=reason,
    )
    return recalled


def recall_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """What the asked look-up found, or that memory holds nothing on it, so the reply owns the gap
    instead of guessing. In a scene an empty look-up adds nothing: what they mean is most likely
    in the story itself, in view, and "memory holds nothing" would make it deny what it can see."""
    del so_far
    recalled = cast("Recalled | None", found)
    if recalled is None or (m.in_scene is not Frame.REAL and not recalled.picked):
        return Offer()
    return Offer((recall_note(recalled.picked),))


RECALL = Feature("recall", look=recall_for_turn, note=recall_offer, scene_read=True)
RELEVANCE = Feature("relevant", look=relevant_for_turn, note=relevant_offer, shadow=shadow_for_turn)
