"""Embedding memories that have no vector yet, for every part of memory that compares meanings
(the relevance look-up, the nightly check)."""

from __future__ import annotations

from datetime import datetime

from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.core.vectors import Embedder
from companion.store.sqlite.store import Store

EMBED_BATCH = 100


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
