"""Judging new replies for callbacks, within a spend cap. Each turn is judged once, through the
judge runner; a failed or unreadable read leaves the turn for the next run."""

from __future__ import annotations

import logging
from datetime import datetime

from companion.core.card import memories_from_card
from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId
from companion.features.audits.callbacks.logic import (
    PROMPT,
    SCHEMA,
    build_prompt,
    label,
    parse,
)
from companion.kit.ask import Judge, ask, whole_answer
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.callbacks")
TIMEOUT_SECONDS = 30.0  # a command, not a turn: no reply waits on it
# The memories it names are checked against the ones shown, so the caller finishes the reading.
CHECK = Judge(
    "callbacks",
    PROMPT,
    SCHEMA,
    whole_answer,
    timeout=TIMEOUT_SECONDS,
    unread="the turn is left for the next run",
)


async def check_new(
    store: Store, extractor: StructuredModel, rel: RelationshipId, since: datetime, cap_usd: float
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
        got = await ask(extractor, CHECK, build_prompt(turn.recent, labelled, turn.reply))
        check = None if got is None else parse(got.value, labelled)
        if got is None or check is None:  # no callback it can name is left for the next run
            continue
        spent += got.cost_usd
        store.add_callback_check(rel, turn.turn_id, check, got.model, got.ref, utc_now())
        judged += 1
    return judged, spent
