"""Reading the companion's own messages for the promises it made (J12). Runs in the open-loop
pass's batch and keeps its bookmark, so a failed call is read again. Shadow only: nothing reaches
the talker."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, tzinfo

from companion.core.beliefs.extract import build_user_prompt
from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import Json, Utterance, UtteranceId
from companion.features.promises.logic import PROMPT, SCHEMA, SYSTEM, parse, to_promise
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.promises")
Log = Callable[[str, dict[str, Json]], None]


async def read_promises(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: Extractor,
    window: Mapping[str, Utterance],
    targets: set[UtteranceId],
    when: tuple[datetime, tzinfo],
    note: Log,
) -> float | None:
    """Record the promises in its targeted messages. The cost, or None when the call failed so the
    batch is read again."""
    now, tz = when
    try:
        with purpose("promises"):
            result = await extractor.extract(
                SYSTEM, build_user_prompt(window, targets, {}, tz), SCHEMA
            )
    except Exception:
        log.warning("promise read failed; the batch is kept for another try", exc_info=True)
        return None
    proposed = parse(result.data)
    if proposed is None:
        note("promises: the answer was malformed and was ignored", {"model": result.model})
        return result.cost_usd
    rel = next(iter(window.values())).relationship_id
    known = {(r.promise.utterance_id, r.promise.quote.lower()) for r in store.promises(rel)}
    for p in proposed:
        outcome = to_promise(p, window, uuid.uuid4().hex)
        if isinstance(outcome, str):
            note(f"promise dropped: {outcome}", {"quote": p.quote, "claim": p.claim})
            continue
        if (outcome.utterance_id, outcome.quote.lower()) in known:
            continue
        store.add_promise(outcome, model=result.model, prompt=PROMPT.ref, at=now)
        known.add((outcome.utterance_id, outcome.quote.lower()))
        note(
            "promise recorded from its own words (shadow)",
            {
                "promise_id": outcome.id,
                "kind": outcome.kind,
                "claim": outcome.claim,
                "quote": outcome.quote,
                "avoid": outcome.avoid,
                "prompt": PROMPT.ref,
            },
        )
    return result.cost_usd
