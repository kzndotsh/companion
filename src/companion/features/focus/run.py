"""The focus look-up: how close each memory is to their message, for the card (`core/card.py`)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from companion.core import switch
from companion.core.card import Focus
from companion.core.spend import purpose
from companion.core.switch import Mode
from companion.core.types import Speaker
from companion.core.vectors import unit
from companion.features.focus.logic import closeness, moment_texts
from companion.kit.current import mark
from companion.kit.embed import LOOK_SECONDS, bounded, embed_missing, embedder_in
from companion.kit.features import Feature, Moment

if TYPE_CHECKING:
    pass

log = logging.getLogger("companion.focus")


async def focus_for_turn(m: Moment) -> Focus | None:
    """With the focus on, every memory's closeness to the moment, scenes included. None when it is
    off, there is no embedder, or the look-up failed or ran past `LOOK_SECONDS`: the card is then
    built as before."""
    c, t = m.c, m.t
    embedder = embedder_in(c, switch.FOCUS, Mode.ON)
    if embedder is None:
        return None
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]

    async def look() -> Focus:
        await embed_missing(c.store, embedder, c.rel, c.embed_model, t.now)
        with purpose("focus"):
            got = await embedder.embed(moment_texts(t.text, replies[-1] if replies else None))
        vectors = c.store.belief_embeddings(c.rel, c.embed_model)
        return Focus(closeness([unit(q) for q in got.vectors], vectors), vectors)

    found = await bounded(
        look(), deadline=LOOK_SECONDS, what="focus look-up", unread="the card is built as before"
    )
    if found is None:
        return None
    mark(t, f"focus: {len(found.closeness)} memories scored")
    return found


FOCUS = Feature("focus", look=focus_for_turn, switch=switch.FOCUS, look_seconds=LOOK_SECONDS)
