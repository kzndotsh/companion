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

from companion.core.extractor import Extractor
from companion.core.relevance import (
    PROMPT,
    SCHEMA,
    Embedder,
    build_prompt,
    eligible,
    nearest,
    parse,
)
from companion.core.spend import purpose
from companion.core.types import Belief, BeliefId, Json, RelationshipId
from companion.loops.ask import Judge, ask
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.relevance")
TIMEOUT_SECONDS = 10.0
EMBED_BATCH = 100
SHOWN = 3


@dataclass(frozen=True, slots=True)
class Lookup:
    """What one shadow look-up found, for the decision detail."""

    detail: dict[str, Json]


async def embed_missing(
    store: Store, embedder: Embedder, rel: RelationshipId, model: str, now: datetime
) -> float:
    """Embed every current memory that has no vector for this model yet. Returns the cost."""
    have = store.belief_embeddings(rel, model)
    todo = [b for b in store.user_beliefs(rel) if b.id not in have]
    cost = 0.0
    for i in range(0, len(todo), EMBED_BATCH):
        chunk = todo[i : i + EMBED_BATCH]
        with purpose("relevance"):
            got = await embedder.embed([b.claim for b in chunk])
        store.add_belief_embeddings(
            rel, {b.id: v for b, v in zip(chunk, got.vectors, strict=True)}, model, now
        )
        cost += got.cost_usd
    return cost


def _row(b: Belief, on_card: set[BeliefId], score: float | None = None) -> dict[str, Json]:
    row: dict[str, Json] = {"id": b.id, "claim": b.claim, "on_card": b.id in on_card}
    if score is not None:
        row["score"] = round(score, 3)
    return row


async def look_up(  # noqa: PLR0913
    store: Store,
    embedder: Embedder,
    judge: Extractor,
    rel: RelationshipId,
    *,
    model: str,
    said: str,
    last_reply: str | None,
    sharing: bool,
    on_card: set[BeliefId],
    now: datetime,
    gate: float | None = None,
) -> Lookup:
    """With `gate`, the small model is asked only when the closest memory scores at least that."""
    started = time.perf_counter()
    cost = await embed_missing(store, embedder, rel, model, now)
    texts = [said, f"{last_reply}\n{said}"] if last_reply else [said]
    with purpose("relevance"):
        query = await embedder.embed(texts)
    embed_ms = int((time.perf_counter() - started) * 1000)
    cost += query.cost_usd
    pool = eligible(store.user_beliefs(rel), sharing=sharing)
    vectors = store.belief_embeddings(rel, model)
    alone = nearest(query.vectors[0], pool, vectors)
    shortlist = nearest(
        query.vectors[-1], pool, vectors
    )  # with their last reply, when there is one
    started = time.perf_counter()
    gated = gate is not None and (not shortlist or shortlist[0][1] < gate)
    picked: list[Belief] = []
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
        if got is not None:
            picked = got.value
            pick_cost, pick_model = got.cost_usd, got.model
    detail: dict[str, Json] = {
        "nearest": [_row(b, on_card, s) for b, s in alone[:SHOWN]],
        "nearest_in_context": [_row(b, on_card, s) for b, s in shortlist[:SHOWN]],
        "picked": [_row(b, on_card) for b in picked],
        "searched": len(pool),
        "embed_ms": embed_ms,
        "pick_ms": int((time.perf_counter() - started) * 1000),
        "cost_usd": round(cost + pick_cost, 6),
        "prompt": PROMPT.ref,
        "embed_model": model,
        "pick_model": pick_model,
        "gated": gated,
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
    judge: Extractor,
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
            ),
            timeout,
        )
    except Exception as err:
        log.warning("relevance look-up failed or timed out: %r", err)
        return None
