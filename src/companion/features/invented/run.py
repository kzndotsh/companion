"""Judging replies for made-up facts about the user (G42), within a spend cap. Each turn once."""

from __future__ import annotations

import logging
from datetime import datetime

from companion.core.card import memories_from_card
from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.spend import purpose
from companion.core.types import RelationshipId, TurnId
from companion.features.invented.logic import PROMPT, SCHEMA, SYSTEM, build_prompt, parse
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.invented")


async def check_new(
    store: Store, extractor: StructuredModel, rel: RelationshipId, since: datetime, cap_usd: float
) -> tuple[int, float]:
    """Judge the turns not judged yet, oldest first, until the cap. Returns (judged, spent)."""
    judged, spent = 0, 0.0
    seen: set[TurnId] = set()
    for turn in store.invented_unchecked(rel, since):
        if spent >= cap_usd:
            log.info("made-up facts check stopped at the $%.2f cap", cap_usd)
            break
        if turn.turn_id in seen:
            continue
        seen.add(turn.turn_id)
        prompt = build_prompt(turn.recent, memories_from_card(turn.card), turn.reply)
        try:
            with purpose("invented"):
                result = await extractor.extract(SYSTEM, prompt, SCHEMA)
        except Exception as err:  # a failed call skips the turn, never the run
            log.warning(
                "made-up facts check on %s failed; left for next time: %r", turn.turn_id, err
            )
            continue
        spent += result.cost_usd
        statements = parse(result.data, turn.reply)
        if statements is None:
            continue
        store.add_invented_check(
            rel, turn.turn_id, statements, judge=result.model, prompt=PROMPT.ref, at=utc_now()
        )
        judged += 1
    return judged, spent
