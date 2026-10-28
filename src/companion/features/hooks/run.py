"""Whether memory already states a basic fact (the J48 hook), with a time limit. A failure or a slow
model only means no shadow pick this turn."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.extractor import StructuredModel
from companion.core.recall import SCHEMA, build_prompt, candidates, parse
from companion.core.types import Belief, Frame, Speaker
from companion.features.hooks.logic import (
    KNEW,
    PROMPT,
    TOPIC,
    WOULD_ASK,
    agreed,
    may_ask,
    read_basic,
)
from companion.features.hooks.logic import SCHEMA as HOOK_SCHEMA
from companion.loops.ask import Judge, ask
from companion.loops.current import Heard, Turn, decide, is_casual
from companion.loops.features import Feature
from companion.loops.reads import read_times
from companion.prompts import get

if TYPE_CHECKING:
    from companion.loops.runtime import Runtime

log = logging.getLogger("companion.hooks")
KNOWN = get("system/basics-known")
TIMEOUT_SECONDS = 5.0


async def stated(
    extractor: StructuredModel, beliefs: Sequence[Belief], topic: str
) -> list[Belief] | None:
    """The memories that state the fact outright, or None when the call failed or was slow."""
    labelled = candidates(beliefs)
    if not labelled:
        return []
    judge = Judge(
        "hook",
        KNOWN,
        SCHEMA,
        lambda data: parse(data, labelled),
        timeout=TIMEOUT_SECONDS,
        unread="no shadow pick this turn",
    )
    got = await ask(extractor, judge, build_prompt(topic, labelled))
    return None if got is None else got.value


async def hook_in_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """On a casual turn, ask a small judge which basic their message touches and log whether code
    would ask about it (J48 hook, shadow). Nothing reaches the talker."""
    del card
    if c.judge is None or not is_casual(t, in_scene, heard):
        return
    last = [u.text for u in t.prior if u.speaker is Speaker.COMPANION][-1:]
    said = (f"COMPANION: {last[0]}\n" if last else "") + f"USER: {t.text}"
    got = await read_times(
        c.judge, PROMPT.text, said, HOOK_SCHEMA, read_basic, spend="hook", timeout=TIMEOUT_SECONDS
    )
    basic = agreed(got.values)  # a failed read means no shadow pick this turn
    asked = [
        (str(d.detail.get("basic")), d.at)
        for key in (WOULD_ASK, KNEW)
        for d in c.store.decisions_with_key(c.rel, key)
        if isinstance(d.detail, dict)
    ]
    if basic is None or not may_ask(basic, asked, t.now):
        return
    found = await stated(c.judge, c.store.user_beliefs(c.rel), TOPIC[basic])
    if found is None:
        return
    decide(
        c,
        t,
        KNEW if found else WOULD_ASK,
        {
            "basic": basic.value,
            "said": t.text,
            "known": [b.claim for b in found],
            "model": got.model,
            "prompt": PROMPT.ref,
        },
    )


# The basics their own words touch without giving, read beside the turn (J48 hook).
HOOKS = Feature("hooks", shadow=hook_in_turn)
