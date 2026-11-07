"""Embedding, for every part of memory that compares meanings (the relevance look-up, the nightly
check): memories that have no vector yet, and the one way a look-up is bounded. A look-up that
fails or runs past its deadline is logged with what that means and gives None; the caller goes on
as it would without it."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.spend import purpose
from companion.core.switch import Mode, Switch
from companion.core.types import RelationshipId
from companion.core.vectors import Embedded, Embedder, Vector
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.embed")
EMBED_BATCH = 100
LOOK_SECONDS = 2.0  # a slow embedding look-up only leaves its part out of this turn


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


def embedder_in(c: Runtime, row: Switch, *modes: Mode) -> Embedder | None:
    """The turn's embedder, only while the switch stands in one of `modes` and there is an embedder:
    the guard every embedding look-up starts with."""
    return c.embedder if c.mode(row) in modes else None


@dataclass(frozen=True, slots=True)
class Queried[K]:
    """Their message as a vector, the vectors of texts that had none yet (by key) and the cost."""

    query: Vector
    fresh: dict[K, Vector]
    cost_usd: float


async def embed_query[K](  # noqa: PLR0913
    embedder: Embedder,
    said: str,
    missing: Sequence[tuple[K, str]],
    *,
    spend: str,
    unread: str,
    deadline: float = LOOK_SECONDS,
) -> Queried[K] | None:
    """What a nearest look-up embeds in one call: the moment's text, then every text with no vector
    yet, each keyed. The caller keeps the fresh vectors in its own table. None as `embed_within`."""
    got = await embed_within(
        embedder,
        [said, *(text for _, text in missing)],
        spend=spend,
        deadline=deadline,
        unread=unread,
    )
    if got is None:
        return None
    fresh = dict(zip((key for key, _ in missing), got.vectors[1:], strict=True))
    return Queried(got.vectors[0], fresh, got.cost_usd)


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
