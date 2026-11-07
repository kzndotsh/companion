"""Recording when they step away, and the tick that drafts a nudge when they stay gone (shadow).
Nothing here sends a message."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.clock import local_midnight
from companion.core.extractor import StructuredModel
from companion.core.reachout import DRAFT_SCHEMA, WOULD_NUDGE, Held, Kind, drafted, parse_draft
from companion.core.turn.now import KEY as NOW_KEY
from companion.core.turn.now import from_decisions
from companion.core.types import Json, RelationshipId, Speaker
from companion.features.nudges.logic import (
    DRAFT,
    GONE,
    RECENT,
    Look,
    aways,
    draft_prompt,
    due,
    newest,
)
from companion.kit.ask import Judge, ask
from companion.kit.features import Feature, Move
from companion.kit.reachdraft import DraftKeys, record_draft
from companion.kit.record import Recorder
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.kit.features import Round
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.nudges")
DRAFTER = Judge(
    "nudge-draft",
    DRAFT,
    DRAFT_SCHEMA,
    parse_draft,
    timeout=30.0,  # one short message
    unread="the nudge is dropped and that time away is not tried again",
    spend="initiative",  # every reach-out's drafting is one line in `companion spend`
)
NUDGE_DROPPED = "nudge (shadow): draft dropped, not sent"
KEYS = DraftKeys(NUDGE_DROPPED, WOULD_NUDGE)


def _look(store: Store, rel: RelationshipId, now: datetime) -> Look:
    theirs = [u.at for u in store.history_before(rel, now, RECENT) if u.speaker is Speaker.USER]
    sent = store.decisions_with_key(rel, WOULD_NUDGE)
    tried = [*sent, *store.decisions_with_key(rel, NUDGE_DROPPED)]
    nudged = frozenset(
        str(d.detail.get("turn"))
        for d in tried
        if isinstance(d.detail, dict) and d.detail.get("turn")
    )
    today = sum(1 for d in sent if d.at >= local_midnight(now))
    said = from_decisions(store.decisions_with_key(rel, NOW_KEY, now - GONE))
    return Look(newest(aways(said)), max(theirs, default=None), nudged, today)


async def tick_nudge(
    store: Store,
    rel: RelationshipId,
    now: datetime,
    extractor: StructuredModel | None,
    *,
    held: Held | None,
) -> str | None:
    """One look, with the shared gate's hold: when a time away is due a nudge, draft it and record
    it (shadow). The draft, or None when nothing was due or the draft failed or read as needy; a
    dropped draft is logged and that time away is not tried again."""
    away, reason = due(_look(store, rel, now), now, held)
    if away is None:
        log.debug("nudge: %s", reason)
        return None
    got: tuple[str, str | None] = ("", "no drafter")
    if extractor is not None:
        read = await ask(extractor, DRAFTER, draft_prompt(away, now))
        got = drafted(
            None if read is None else read.value, "the draft call failed or had no message"
        )
    text, dropped = got
    detail: dict[str, Json] = {"turn": away.turn, "said": away.said, "prompt": DRAFT.ref}
    if text:
        detail["draft"] = text
    else:
        detail["why"] = dropped
    record_draft(Recorder.fresh(store, rel, now), KEYS, got, detail, f"{WOULD_NUDGE}: {reason}")
    if not text:
        log.info("nudge dropped: %s", dropped)
        return None
    log.info("nudge shadow: would send %r (%s)", text, reason)
    return text


def reaching(c: Runtime) -> tuple[Move, ...]:
    """Its step in the initiative tick: a nudge after they stepped away, when no plan went first."""

    async def nudge(r: Round) -> None:
        if r.first is None and await tick_nudge(c.store, c.rel, r.now, c.judge, held=r.held):
            r.first = Kind.AWAY

    return (Move(Kind.AWAY, nudge),)


NUDGES = Feature("nudge", reaching=reaching)
