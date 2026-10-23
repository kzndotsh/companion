"""What runs beside a turn and never changes the reply: shadow look-ups, each logged, a failure
logged too (the shadow stage of a turn)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.extractor import Extractor
from companion.core.hooks import KNEW as HOOK_KNEW
from companion.core.hooks import PROMPT as HOOK_PROMPT
from companion.core.hooks import SCHEMA as HOOK_SCHEMA
from companion.core.hooks import TOPIC as HOOK_TOPIC
from companion.core.hooks import WOULD_ASK as HOOK_WOULD_ASK
from companion.core.hooks import agreed, may_ask, read_basic
from companion.core.nudges import AWAY as AWAY_REASON
from companion.core.nudges import PROMPT as AWAY_PROMPT
from companion.core.nudges import SCHEMA as AWAY_SCHEMA
from companion.core.nudges import parse as parse_away
from companion.core.recheck import SERIOUS as RECHECK_SERIOUS
from companion.core.types import (
    DecisionKind,
    Frame,
    Speaker,
)
from companion.loops.ask import Judge, ask
from companion.loops.hooks import TIMEOUT_SECONDS as HOOK_TIMEOUT
from companion.loops.hooks import stated
from companion.loops.reads import read_times
from companion.loops.registry import FEATURES
from companion.loops.turn import Heard, Turn, decide, is_casual

if TYPE_CHECKING:
    from companion.loops.fast import Conversation

log = logging.getLogger("companion.turn")
AWAY_JUDGE = Judge(
    "nudge", AWAY_PROMPT, AWAY_SCHEMA, parse_away, timeout=8.0, unread="no nudge for this message"
)


_BESIDE: set[asyncio.Task[None]] = set()  # shadow look-ups still running, kept from collection


def beside(job: Coroutine[object, object, None]) -> None:
    """Run a shadow look-up beside the turn, kept from collection until it ends. A failure is
    logged, never raised and never silent."""
    task = asyncio.get_running_loop().create_task(job)
    _BESIDE.add(task)

    def done(finished: asyncio.Task[None]) -> None:
        _BESIDE.discard(finished)
        if not finished.cancelled() and finished.exception() is not None:
            log.warning("shadow look-up failed: %r", finished.exception())

    task.add_done_callback(done)


def shadows(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, card: Card) -> None:
    """What runs in shadow on a turn and never changes the reply: each feature's shadow look-up,
    whether they are stepping away, and the basic it would ask about."""
    for feature in FEATURES:
        if feature.shadow is not None:
            beside(feature.shadow(c, t, in_scene, heard, card))
    _hook_beside(c, t, in_scene, heard)
    _away_beside(c, t, in_scene, heard)


def _away_beside(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> None:
    """Record when they say they are stepping away and for about how long, so the tick can nudge
    if they stay gone (shadow). Runs beside any real, not serious turn, not only casual ones:
    "gotta run" is exactly the message to read, and the judge tells a goodbye apart."""
    serious = heard is None or heard[0].severity >= RECHECK_SERIOUS
    if c.judge is None or serious or in_scene is not Frame.REAL:
        return

    async def run(judge: Extractor) -> None:
        got = await ask(judge, AWAY_JUDGE, f"USER: {t.text}")
        if got is None:
            return
        read = got.value
        decide(
            c,
            t,
            AWAY_REASON,
            {
                "kind": read[0].value,
                "minutes": read[1],
                "said": t.text,
                "model": got.model,
                "prompt": got.ref,
            },
        )

    beside(run(c.judge))


def _hook_beside(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> None:
    """On a casual turn, ask a small judge which basic their message touches and log whether code
    would ask about it (J48 hook, shadow). Runs beside the turn; nothing reaches the talker."""
    if c.judge is None or not is_casual(t, in_scene, heard):
        return
    beliefs = c.store.user_beliefs(c.rel)
    asked = [
        (str(d.detail.get("basic")), d.at)
        for d in c.store.decisions_of_kind(c.rel, DecisionKind.POLICY)
        if (d.has_key(HOOK_WOULD_ASK) or d.has_key(HOOK_KNEW)) and isinstance(d.detail, dict)
    ]

    async def run(judge: Extractor) -> None:
        last = [u.text for u in t.prior if u.speaker is Speaker.COMPANION][-1:]
        said = (f"COMPANION: {last[0]}\n" if last else "") + f"USER: {t.text}"
        got = await read_times(
            judge,
            HOOK_PROMPT.text,
            said,
            HOOK_SCHEMA,
            read_basic,
            spend="hook",
            timeout=HOOK_TIMEOUT,
        )
        basic = agreed(got.values)  # a failed read means no shadow pick this turn
        if basic is None or not may_ask(basic, asked, t.now):
            return
        found = await stated(judge, beliefs, HOOK_TOPIC[basic])
        if found is None:
            return
        knew = bool(found)
        decide(
            c,
            t,
            HOOK_KNEW if knew else HOOK_WOULD_ASK,
            {
                "basic": basic.value,
                "said": t.text,
                "known": [b.claim for b in found],
                "model": got.model,
                "prompt": HOOK_PROMPT.ref,
            },
        )

    beside(run(c.judge))
