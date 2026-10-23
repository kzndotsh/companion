"""List the names in memories not read yet (fetch on mention, shadow). Runs after the memory pass
and from the CLI. A failed call reads nothing and is tried again next pass."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.extractor import Extractor
from companion.core.names import BATCH, PROMPT, SCHEMA, parse, prompt
from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.loops.features import Feature
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.names")


@dataclass(frozen=True, slots=True)
class NamesRead:
    read: int = 0
    names: int = 0
    left: int = 0
    cost_usd: float = 0.0


async def read_names(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime, *, batches: int = 1
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


NAMES = Feature("names", after_theirs=read_names)  # the names in new memories, for fetch on mention
