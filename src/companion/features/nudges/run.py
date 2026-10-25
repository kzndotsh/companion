"""Recording when they step away, and the tick that drafts a nudge when they stay gone (shadow).
Nothing here sends a message."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.clock import local_midnight
from companion.core.extractor import Extractor
from companion.core.reachout import WOULD_NUDGE, Held, checked
from companion.core.recheck import SERIOUS as RECHECK_SERIOUS
from companion.core.spend import purpose
from companion.core.types import (
    DecisionKind,
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
)
from companion.features.nudges.logic import (
    AWAY,
    DRAFT,
    DRAFT_SCHEMA,
    PROMPT,
    SCHEMA,
    Away,
    Kind,
    Look,
    draft_prompt,
    due,
    newest,
    read,
)
from companion.loops.ask import Judge, ask
from companion.loops.current import Heard, Turn, decide
from companion.loops.features import Feature
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.nudges")
SESSION = SessionId("initiative")
NUDGE_DROPPED = "nudge (shadow): draft dropped, not sent"


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = uuid.uuid4().hex
    return Recorder(store, rel, SESSION, TurnId(trace), TraceId(trace), now)


def aways(store: Store, rel: RelationshipId) -> list[Away]:
    out: list[Away] = []
    for d in store.decisions_with_key(rel, AWAY):
        if not isinstance(d.detail, dict):
            continue
        kind, minutes, said = d.detail.get("kind"), d.detail.get("minutes"), d.detail.get("said")
        if kind in set(Kind) and isinstance(minutes, int) and isinstance(said, str):
            out.append(Away(str(d.turn_id), said, Kind(str(kind)), minutes, d.at))
    return out


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
    return Look(newest(aways(store, rel)), max(theirs, default=None), nudged, today)


async def tick_nudge(
    store: Store,
    rel: RelationshipId,
    now: datetime,
    extractor: Extractor | None,
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
        try:
            with purpose("initiative"):
                got = await extractor.extract(DRAFT.text, draft_prompt(away, now), DRAFT_SCHEMA)
            message = got.data.get("message") if isinstance(got.data, dict) else None
            text, dropped = checked(message) if isinstance(message, str) else ("", "no message")
        except Exception:
            log.warning("could not draft the nudge", exc_info=True)
            dropped = "the draft call failed"
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
            "kind": away.kind,
            "draft": text,
            "prompt": DRAFT.ref,
        },
        reason=f"{WOULD_NUDGE}: {reason}",
        kind=DecisionKind.INITIATE,
    )
    log.info("nudge shadow: would send %r (%s)", text, reason)
    return text


AWAY_JUDGE = Judge("nudge", PROMPT, SCHEMA, read, timeout=8.0, unread="no nudge for this message")


async def away_in_turn(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """Record when they say they are stepping away and for about how long, so the tick can nudge
    if they stay gone (shadow). Runs beside any real, not serious turn, not only casual ones:
    "gotta run" is exactly the message to read, and the judge tells a goodbye apart."""
    del card
    serious = heard is None or heard[0].severity >= RECHECK_SERIOUS
    if not c.initiative or c.judge is None or serious or in_scene is not Frame.REAL:
        return
    got = await ask(c.judge, AWAY_JUDGE, f"USER: {t.text}")
    if got is None or got.value.away is None:
        return
    kind, minutes = got.value.away
    decide(
        c,
        t,
        AWAY,
        {
            "kind": kind.value,
            "minutes": minutes,
            "said": t.text,
            "model": got.model,
            "prompt": got.ref,
        },
    )


# Whether they are stepping away, read beside the turn; the nudge itself is drafted by the tick.
NUDGES = Feature("nudges", shadow=away_in_turn)
