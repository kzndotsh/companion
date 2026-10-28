"""List the names in memories not read yet (fetch on mention, shadow). Runs after the memory pass
and from the CLI. A failed call reads nothing and is tried again next pass."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.card import HOLD_AT, Card
from companion.core.extractor import StructuredModel
from companion.core.frames import is_assertable
from companion.core.spend import purpose
from companion.core.types import Frame, RelationshipId
from companion.features.names.logic import (
    BATCH,
    PROMPT,
    SCHEMA,
    SHADOW,
    index,
    mentioned,
    parse,
    prompt,
)
from companion.loops.current import Heard, Turn, decide
from companion.loops.features import Feature
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.loops.runtime import Runtime

log = logging.getLogger("companion.names")


@dataclass(frozen=True, slots=True)
class NamesRead:
    read: int = 0
    names: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def read_names(
    store: Store,
    extractor: StructuredModel,
    rel: RelationshipId,
    now: datetime,
    *,
    batches: int = 1,
) -> NamesRead:
    done = found = 0
    cost = 0.0
    for _ in range(batches):
        seen = store.names_read(rel)
        todo = [b for b in store.user_beliefs(rel) if b.id not in seen][:BATCH]
        if not todo:
            break
        text, refs = prompt([(b.id, b.claim) for b in todo], {r.name for r in store.name_rows(rel)})
        try:
            with purpose("names"):
                result = await extractor.extract(PROMPT.text, text, SCHEMA)
        except Exception as err:
            log.warning("memory names failed: %r", err)
            break
        cost += result.cost_usd
        rows = parse(result.data, refs)
        if rows is None:
            log.warning("memory names: the answer was malformed and was ignored")
            break
        store.add_names(rel, rows, refs.values(), model=result.model, prompt=PROMPT.ref, at=now)
        done += len(refs)
        found += len({r.name for r in rows})
    seen = store.names_read(rel)
    left = sum(b.id not in seen for b in store.user_beliefs(rel))
    log.debug("memory names: %d read, %d names, %d left, $%.4f", done, found, left, cost)
    return NamesRead(done, found, left, cost)


async def named_in_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """When their message names something memory knows, log the memories about it that the card
    left out (shadow, code only). Nothing reaches the talker."""
    if heard is None or in_scene is not Frame.REAL:
        return
    sharing = heard[0].severity >= 1
    visible = {
        b.id
        for b in c.store.user_beliefs(c.rel)
        if is_assertable(b) and (sharing or b.sensitivity < HOLD_AT)
    }
    named = mentioned(t.text, index(c.store.name_rows(c.rel), visible))
    if not named:
        return
    on_card = {b.id for b in (*card.usable, *card.held, *card.older)}
    about = {bid for n in named for bid in n.beliefs}
    decide(
        c,
        t,
        SHADOW,
        {
            "names": [str(n.name) for n in named],
            "would_add": [str(b) for b in sorted(about - on_card)],
            "on_card": [str(b) for b in sorted(about & on_card)],
        },
    )


# The names in new memories, read after a memory pass; matched against their message in shadow.
NAMES = Feature("names", after_theirs=read_names, shadow=named_in_turn)
