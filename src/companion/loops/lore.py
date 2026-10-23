"""Label the companion's views that have no kind yet (ADR 0020, phase 1). Runs after the memory pass
and from the CLI. A failed call labels nothing and is tried again next pass."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from companion.core.extractor import Extractor
from companion.core.lore import (
    BATCH,
    GATE,
    PROMPT,
    SCHEMA,
    SHOWN,
    agreed,
    lore,
    lore_note,
    parse,
    prompt,
)
from companion.core.relevance import Embedder, nearest
from companion.core.spend import purpose
from companion.core.types import Belief, BeliefId, Frame, RelationshipId
from companion.loops.features import Feature, Offer
from companion.loops.reads import read_times
from companion.loops.turn import Heard, Turn, decide, is_casual
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.loops.fast import Conversation
    from companion.loops.notes import Moment

log = logging.getLogger("companion.lore")


@dataclass(frozen=True, slots=True)
class KindsRead:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def label_views(  # noqa: PLR0913
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
    again: bool = False,
) -> KindsRead:
    """Label views with no kind yet, READS times each, keeping a taste only where every read
    agrees. `again` labels every current view anew (the newest label wins)."""
    done = 0
    cost = 0.0
    redo = {b.id for b in store.self_beliefs(rel)} if again else set[BeliefId]()
    for _ in range(batches):
        have = store.view_kinds(rel)
        todo = [b for b in store.self_beliefs(rel) if b.id in redo or b.id not in have][:BATCH]
        if not todo:
            break
        redo -= {b.id for b in todo}
        text, refs = prompt(todo)
        got = await read_times(
            extractor,
            PROMPT.text,
            text,
            SCHEMA,
            lambda data, shown=refs: parse(data, shown),
            spend="lore",
        )
        cost += got.cost_usd
        if got.failed:  # the batch is labelled again next time, never from fewer reads
            log.warning("view kinds: a read failed; the batch waits for the next pass")
            break
        found = agreed(got.values, refs.values())
        store.add_view_kinds(rel, found, model=got.model, prompt=PROMPT.ref, at=now)
        done += len(found)
    have = store.view_kinds(rel)
    left = sum(b.id not in have for b in store.self_beliefs(rel))
    log.debug("view kinds: %d labelled, %d left, $%.4f", done, left, cost)
    return KindsRead(done, left, cost)


LOOK_SECONDS = 2.0  # a slow embedding only means no tastes are shown this turn


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
    """Its tastes nearest their message, at most SHOWN and none below GATE, embedding any taste that
    has no vector yet in the same call. None when the call failed or was slow."""
    tastes = lore(store.self_beliefs(rel), store.view_kinds(rel))
    if not tastes:
        return Nearest((), 0.0)
    have = store.belief_embeddings(rel, model)
    missing = [b for b in tastes if b.id not in have]
    try:
        with purpose("lore"):
            got = await asyncio.wait_for(
                embedder.embed([said, *(b.claim for b in missing)]), LOOK_SECONDS
            )
    except Exception as err:
        log.warning("lore look-up failed or was slow; no tastes shown: %r", err)
        return None
    if missing:
        fresh = dict(zip((b.id for b in missing), got.vectors[1:], strict=True))
        store.add_belief_embeddings(rel, fresh, model, now)
        have = {**have, **fresh}
    near = nearest(got.vectors[0], tastes, have, k=SHOWN)
    return Nearest(tuple((b, s) for b, s in near if s >= GATE), got.cost_usd)


LORE_SHOWN = "lore: its own tastes nearest their message"


async def tastes_for_turn(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[str, ...]:
    """Its tastes nearest their message on an ordinary turn (ADR 0020), as the words it said. In
    shadow they are logged and not shown."""
    if c.lore == "off" or c.embedder is None or not is_casual(t, in_scene, heard):
        return ()
    found = await nearest_tastes(c.store, c.embedder, c.rel, c.embed_model, t.text, t.now)
    if found is None or not found.tastes:
        return ()
    decide(
        c,
        t,
        LORE_SHOWN + ("" if c.lore == "on" else " (shadow)"),
        {
            "tastes": [str(b.id) for b, _ in found.tastes],
            "scores": [round(s, 3) for _, s in found.tastes],
            "claims": [b.claim for b, _ in found.tastes],
        },
    )
    return tuple(b.evidence[0].quote for b, _ in found.tastes) if c.lore == "on" else ()


def lore_offer(m: Moment, found: object) -> Offer:
    """Its tastes as the words it said, in one note (`notes/lore`)."""
    del m
    quotes = cast("tuple[str, ...]", found or ())
    note = lore_note(f'you said: "{q}"' for q in quotes)
    return Offer((note,) if note else ())


LORE = Feature("lore", look=tastes_for_turn, note=lore_offer)
