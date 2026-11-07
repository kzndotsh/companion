"""Label the companion's views that have no kind yet (ADR 0020, phase 1). Runs after the memory pass
and from the CLI. A failed call labels nothing and is tried again next pass."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from companion.core import switch
from companion.core.extractor import StructuredModel
from companion.core.switch import Mode
from companion.core.types import Belief, BeliefId, Frame, RelationshipId
from companion.core.vectors import NEAR_AT, Embedder, nearest
from companion.features.lore.logic import (
    BATCH,
    PROMPT,
    SCHEMA,
    SHOWN,
    agreed,
    lore,
    lore_note,
    parse,
    prompt,
)
from companion.features.lore.store import ViewKinds
from companion.kit.batches import Batch, Swept, label_in_batches
from companion.kit.current import Heard, Turn, decide, is_casual
from companion.kit.embed import embed_query, embedder_in
from companion.kit.features import Feature, Offer, Offered
from companion.kit.reads import read_times
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.lore")


async def label_views(  # noqa: PLR0913
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
    again: bool = False,
) -> Swept:
    """Label views with no kind yet, READS times each, keeping a taste only where every read
    agrees. `again` labels every current view anew (the newest label wins)."""
    redo = {b.id for b in store.self_beliefs(rel)} if again else set[BeliefId]()

    def todo() -> list[Belief]:
        have = store.view_kinds(rel)
        return [b for b in store.self_beliefs(rel) if b.id in redo or b.id not in have][:BATCH]

    async def label(views: Sequence[Belief]) -> Batch:
        redo.difference_update(b.id for b in views)
        text, refs = prompt(views)
        got = await read_times(
            extractor,
            PROMPT.text,
            text,
            SCHEMA,
            lambda data: parse(data, refs),
            spend="lore",
            timeout=60.0,  # a batch of views, three reads at once
        )
        if got.failed:  # the batch is labelled again next time, never from fewer reads
            log.warning("view kinds: a read failed; the batch waits for the next pass")
            return Batch(cost_usd=got.cost_usd, stop=True)
        found = agreed(got.values, refs.values())
        store.part(ViewKinds).add(rel, found, model=got.model, prompt=PROMPT.ref, at=now)
        return Batch(len(found), got.cost_usd)

    def left() -> int:
        have = store.view_kinds(rel)
        return sum(b.id not in have for b in store.self_beliefs(rel))

    return await label_in_batches("view kinds", batches=batches, todo=todo, label=label, left=left)


@dataclass(frozen=True, slots=True)
class Nearest:
    tastes: tuple[tuple[Belief, float], ...]
    cost_usd: float


async def nearest_tastes(  # noqa: PLR0913, PLR0917
    store: Store,
    embedder: Embedder,
    rel: RelationshipId,
    model: str,
    said: str,
    now: datetime,
) -> Nearest | None:
    """Its tastes nearest their message, at most SHOWN and none below NEAR_AT, embedding any taste
    that has no vector yet in the same call. None when the call failed or was slow."""
    tastes = lore(store.self_beliefs(rel), store.view_kinds(rel))
    if not tastes:
        return Nearest((), 0.0)
    have = store.belief_embeddings(rel, model)
    missing = [(b.id, b.claim) for b in tastes if b.id not in have]
    got = await embed_query(
        embedder,
        said,
        missing,
        spend="lore",
        unread="no tastes shown",
    )
    if got is None:
        return None
    if got.fresh:
        store.add_belief_embeddings(rel, got.fresh, model, now)
        have = {**have, **got.fresh}
    near = nearest(got.query, tastes, have, k=SHOWN)
    return Nearest(tuple((b, s) for b, s in near if s >= NEAR_AT), got.cost_usd)


LORE_SHOWN = "lore: its own tastes nearest their message"


async def tastes_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[str, ...]:
    """Its tastes nearest their message on an ordinary turn (ADR 0020), as the words it said. In
    shadow they are logged and not shown."""
    embedder = embedder_in(c, switch.LORE, Mode.SHADOW, Mode.ON)
    if embedder is None or not is_casual(t, in_scene, heard):
        return ()
    found = await nearest_tastes(c.store, embedder, c.rel, c.embed_model, t.text, t.now)
    if found is None or not found.tastes:
        return ()
    decide(
        c,
        t,
        LORE_SHOWN + ("" if c.mode(switch.LORE) is Mode.ON else " (shadow)"),
        {
            "tastes": [str(b.id) for b, _ in found.tastes],
            "scores": [round(s, 3) for _, s in found.tastes],
            "claims": [b.claim for b, _ in found.tastes],
        },
    )
    return (
        tuple(b.evidence[0].quote for b, _ in found.tastes)
        if c.mode(switch.LORE) is Mode.ON
        else ()
    )


def lore_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """Its tastes as the words it said, in one note (`notes/lore`)."""
    del m, so_far
    quotes = cast("tuple[str, ...]", found or ())
    note = lore_note(f'you said: "{q}"' for q in quotes)
    return Offer((note,) if note else ())


LORE = Feature("lore", look=tastes_for_turn, note=lore_offer, after_own=label_views)
