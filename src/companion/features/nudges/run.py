"""Recording when they step away, and the tick that drafts a nudge when they stay gone (shadow).
Nothing here sends a message."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.clock import local_midnight
from companion.core.extractor import StructuredModel
from companion.core.reachout import DRAFT_SCHEMA, WOULD_NUDGE, Held, checked, parse_draft
from companion.core.turn.now import KEY as NOW_KEY
from companion.core.turn.now import from_decisions
from companion.core.types import (
    DecisionKind,
    RelationshipId,
    Speaker,
    TraceId,
    TurnId,
)
from companion.features.nudges.logic import (
    DRAFT,
    GONE,
    Look,
    aways,
    draft_prompt,
    due,
    newest,
)
from companion.kit.ask import Judge, ask
from companion.kit.record import Recorder
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    pass

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


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = uuid.uuid4().hex
    return Recorder(store, rel, TurnId(trace), TraceId(trace), now)


def _look(store: Store, rel: RelationshipId, now: datetime) -> Look:
    theirs = [u.at for u in store.history_before(rel, now, 40) if u.speaker is Speaker.USER]
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
    text, dropped = "", "no drafter"
    if extractor is not None:
        got = await ask(extractor, DRAFTER, draft_prompt(away, now))
        if got is None:
            dropped = "the draft call failed or had no message"
        else:
            text, dropped = checked(got.value)
    if not text:
        _record(store, rel, now).decide(
            NUDGE_DROPPED,
            {"turn": away.turn, "said": away.said, "why": dropped, "prompt": DRAFT.ref},
            reason=f"{NUDGE_DROPPED}: {dropped}",
        )
        log.info("nudge dropped: %s", dropped)
        return None
    _record(store, rel, now).decide(
        WOULD_NUDGE,
        {
            "turn": away.turn,
            "said": away.said,
            "draft": text,
            "prompt": DRAFT.ref,
        },
        reason=f"{WOULD_NUDGE}: {reason}",
        kind=DecisionKind.INITIATE,
    )
    log.info("nudge shadow: would send %r (%s)", text, reason)
    return text
