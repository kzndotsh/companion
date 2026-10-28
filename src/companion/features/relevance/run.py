"""The relevance look-up in shadow: what it would have kept in mind this turn, logged, never sent.

Runs beside the turn and never holds the reply up. A failure logs what failed and nothing else.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from companion.core.card import Card
from companion.core.extractor import StructuredModel
from companion.core.spend import purpose
from companion.core.types import Belief, BeliefId, Frame, Json, RelationshipId, Speaker
from companion.core.vectors import Embedder, nearest
from companion.features.relevance.logic import GATE as RELEVANCE_GATE
from companion.features.relevance.logic import LIVE as RELEVANCE_LIVE
from companion.features.relevance.logic import PROMPT, SCHEMA, SHOWN, build_prompt, eligible, parse
from companion.features.relevance.logic import SHADOW as RELEVANCE_SHADOW
from companion.kit.ask import Judge, ask
from companion.kit.current import Heard, Turn, decide, mark
from companion.kit.embed import embed_missing
from companion.kit.features import Feature, Offer, Offered
from companion.prompts import get
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.relevance")
TIMEOUT_SECONDS = 10.0
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
    pool = [b for b in eligible(store.user_beliefs(rel), sharing=sharing) if b.id not in hidden]
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
        picker = Judge(
            "relevance",
            PROMPT,
            SCHEMA,
            lambda data: parse(data, offered),
            timeout=TIMEOUT_SECONDS,
            unread="no memories picked this turn; the nearest are still logged",
        )
        got = await ask(judge, picker, build_prompt(last_reply, said, offered))
        pick_failed = got is None
        if got is not None:
            picked = got.value
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
    try:
        return await asyncio.wait_for(
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
            timeout,
        )
    except Exception as err:
        log.warning("relevance look-up failed or timed out: %r", err)
        return None


def _hidden(c: Runtime) -> frozenset[BeliefId]:
    """The intimate lane, left out of the look-up when the scene memory is on (ADR 0026)."""
    return c.store.scene_memory().intimate(c.rel) if c.scene_memory == "on" else frozenset()


RELEVANT_NOTE = get("notes/relevant")
LIVE_SECONDS = 3.0  # a slow look-up only means no memories are offered this turn


async def relevant_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[tuple[BeliefId, str], ...]:
    """With the look-up on (ADR 0018): the memories a small model picks as bearing on their message,
    asked only when the closest memory is near (GATE), outside a scene. Logged either way. With no
    listening read because the judge failed it still runs, as a turn that is not sharing, so nothing
    held is offered; with listening switched off it does not run, as before."""
    if c.relevance != "on" or c.embedder is None or c.judge is None:
        return ()
    if heard is None and not c.listen:
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
        sharing=heard is not None and heard[0].severity >= 1,
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
    picks = [claim for bid, claim in picked if bid not in m.on_card][:SHOWN]
    if not picks:
        return Offer()
    return Offer((RELEVANT_NOTE.render(items="\n".join(f"- {p}" for p in picks)),))


async def shadow_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """With the look-up in shadow: what it would have kept in mind on an ordinary message, logged
    beside the turn; it never holds up or changes the reply."""
    if (
        c.relevance != "shadow"
        or c.embedder is None
        or c.judge is None
        or (heard is None and not c.listen)
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
        sharing=heard is not None and heard[0].severity >= 1,
        on_card=[b.id for b in (*card.usable, *card.held, *card.older)],
        now=t.now,
        hidden=_hidden(c),
    )
    if found is not None:
        decide(c, t, RELEVANCE_SHADOW, found.detail)


RELEVANCE = Feature("relevant", look=relevant_for_turn, note=relevant_offer, shadow=shadow_for_turn)
