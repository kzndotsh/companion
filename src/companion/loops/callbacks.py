"""Judging new replies for callbacks, within a spend cap. Each turn is judged once."""

from __future__ import annotations

import logging
from datetime import datetime

from companion.core.callbacks import (
    PROMPT,
    SCHEMA,
    SYSTEM,
    build_prompt,
    label,
    memories_from_card,
    parse,
)
from companion.core.clock import utc_now
from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.callbacks")


async def check_new(
    store: Store, extractor: Extractor, rel: RelationshipId, since: datetime, cap_usd: float
) -> tuple[int, float]:
    """Judge the turns not judged yet, oldest first, until the cap. Returns (judged, spent)."""
    judged, spent = 0, 0.0
    for turn in store.callbacks_unchecked(rel, since):
        if spent >= cap_usd:
            log.info("callback check stopped at the $%.2f cap", cap_usd)
            break
        labelled = label(memories_from_card(turn.card))
        if not labelled:
            continue
        try:
            with purpose("callbacks"):
                result = await extractor.extract(
                    SYSTEM, build_prompt(turn.recent, labelled, turn.reply), SCHEMA
                )
        except Exception as err:  # a refused or failed call skips the turn, never the run
            log.warning("callback check on %s failed; left for the next run: %r", turn.turn_id, err)
            continue
        spent += result.cost_usd
        check = parse(result.data, labelled)
        if check is None:
            log.debug("callback check on %s was unreadable; left for the next run", turn.turn_id)
            continue
        store.add_callback_check(rel, turn.turn_id, check, result.model, PROMPT.ref, utc_now())
        judged += 1
    return judged, spent
