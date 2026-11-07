"""Embedding, for every part of memory that compares meanings (the relevance look-up, the nightly
check): memories that have no vector yet, and the one way a look-up is bounded. A look-up that
fails or runs past its deadline is logged with what that means and gives None; the caller goes on
as it would without it."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Sequence
from datetime import datetime

from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.core.vectors import Embedded, Embedder
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.embed")
EMBED_BATCH = 100


async def bounded[T](work: Awaitable[T], *, deadline: float, what: str, unread: str) -> T | None:
    """Run a look-up within `deadline` seconds. None when it failed or ran past it, logged as
    `what` failing with `unread`, what that means for the caller."""
    try:
        return await asyncio.wait_for(work, deadline)
    except Exception as err:
        log.warning("%s failed or was slow; %s: %r", what, unread, err)
        return None


async def embed_within(
    embedder: Embedder, texts: Sequence[str], *, spend: str, deadline: float, unread: str
) -> Embedded | None:
    """The texts embedded, tagged for spend, within `deadline` seconds; None as `bounded`, logged
    as the `spend` look-up."""

    async def embed() -> Embedded:
        with purpose(spend):
            return await embedder.embed(texts)

    return await bounded(embed(), deadline=deadline, what=f"{spend} look-up", unread=unread)


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
