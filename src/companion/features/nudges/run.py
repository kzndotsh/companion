"""Recording when they step away, and the tick that drafts a nudge when they stay gone (shadow).
Nothing here sends a message."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, tzinfo
from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.clock import local_midnight
from companion.core.extractor import Extractor
from companion.core.reachout import Caps, short_draft
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
    WOULD_NUDGE,
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


def _record(store: Store, rel: RelationshipId, now: datetime) -> Recorder:
    trace = uuid.uuid4().hex
    return Recorder(store, rel, SESSION, TurnId(trace), TraceId(trace), now)


def aways(store: Store, rel: RelationshipId) -> list[Away]:
    out: list[Away] = []
    for d in store.decisions_of_kind(rel, DecisionKind.POLICY):
        if not d.has_key(AWAY) or not isinstance(d.detail, dict):
            continue
        kind, minutes, said = d.detail.get("kind"), d.detail.get("minutes"), d.detail.get("said")
        if kind in set(Kind) and isinstance(minutes, int) and isinstance(said, str):
            out.append(Away(str(d.turn_id), said, Kind(str(kind)), minutes, d.at))
    return out


def _look(store: Store, rel: RelationshipId, now: datetime) -> Look:
    theirs = [u.at for u in store.history_before(rel, now, 40) if u.speaker is Speaker.USER]
    sent = [
        d for d in store.decisions_of_kind(rel, DecisionKind.INITIATE) if d.has_key(WOULD_NUDGE)
    ]
    nudged = frozenset(
        str(d.detail.get("turn"))
        for d in sent
        if isinstance(d.detail, dict) and d.detail.get("turn")
    )
    today = sum(1 for d in sent if d.at >= local_midnight(now))
    return Look(newest(aways(store, rel)), max(theirs, default=None), nudged, today)


async def tick_nudge(  # noqa: PLR0913
    store: Store,
    rel: RelationshipId,
    now: datetime,
    tz: tzinfo,
    extractor: Extractor | None,
    *,
    caps: Caps = Caps(),  # noqa: B008
) -> str | None:
    """One look: when a time away is due a nudge, draft it and record it (shadow). The draft, or
    None when nothing was due."""
    away, reason = due(_look(store, rel, now), now, tz, caps)
    if away is None:
        log.debug("nudge: %s", reason)
        return None
    text = ""
    if extractor is not None:
        try:
            with purpose("initiative"):
                got = await extractor.extract(DRAFT.text, draft_prompt(away, now), DRAFT_SCHEMA)
            message = got.data.get("message") if isinstance(got.data, dict) else None
            text = short_draft(message) if isinstance(message, str) else ""
        except Exception:
            log.warning("could not draft the nudge", exc_info=True)
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
