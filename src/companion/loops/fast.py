"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from companion.core.ack import (
    REACT_THRESHOLD,
    Reaction,
    inputs_hash,
    is_candidate,
    reaction_for,
    render_reason,
    schema_hash,
)
from companion.core.card import Card, build_card, render
from companion.core.clock import volatile_line
from companion.core.extractor import Extractor
from companion.core.freshness import HORIZON_DAYS, age_phrase
from companion.core.history import HISTORY_LIMIT, to_messages
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import build_request, request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Talker
from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.views import card_views, why
from companion.loops.ack import judge
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.turn")


def _id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class _CardLog:
    """Records where each belief went this turn: into the card, or held back."""

    store: Store
    rel: RelationshipId
    session: SessionId
    turn: TurnId
    at: datetime
    view_reasons: dict[BeliefId, str]

    def write(self, card: Card) -> None:
        for b in card.usable:
            self._one(DecisionKind.SURFACE, b, "in the card")
        for b in card.held:
            self._one(
                DecisionKind.WITHHOLD, b, f"sensitivity {b.sensitivity}: known, held for listening"
            )
        for b in card.older:
            self._one(DecisionKind.SURFACE, b, "in the card as older, possibly out of date")
        for b in card.dropped:
            self._one(DecisionKind.WITHHOLD, b, self._why_dropped(b, card))
        for b in card.views:
            self._one(DecisionKind.SURFACE, b, self.view_reasons[b.id])

    @staticmethod
    def _why_dropped(b: Belief, card: Card) -> str:
        last = age_phrase(card.now - card.aged[b.id].last_supported)
        horizon = HORIZON_DAYS[b.kind]
        return f"stale: last mentioned {last}, past its {horizon}-day horizon, so left out"

    def _one(self, kind: DecisionKind, belief: Belief, reason: str) -> None:
        self.store.append_decision(
            Decision(
                DecisionId(_id()),
                self.rel,
                self.session,
                self.turn,
                TraceId(self.turn),
                kind,
                reason,
                self.at,
                belief.id,
            )
        )


@dataclass(frozen=True, slots=True)
class Conversation:
    store: Store
    talker: Talker
    prefix: Prefix
    rel: RelationshipId
    judge: Extractor | None = None

    async def handle(
        self, session: SessionId, text: str, channel: str, now: datetime | None = None
    ) -> str | Reaction:
        return await _handle_turn(self, session, text, channel, now)


@dataclass(frozen=True, slots=True)
class _Turn:
    session: SessionId
    turn: TurnId
    now: datetime
    prior: list[Utterance]
    text: str


async def _ack_reaction(c: Conversation, t: _Turn) -> Reaction | None:
    """A reaction if this short message only acknowledges. Logs every judgement it makes."""
    if c.judge is None or not is_candidate(t.text, t.prior):
        return None
    outcome = await judge(c.judge, t.prior, t.text)
    if outcome is None:
        return None
    judged, model, prompt = outcome
    reaction = reaction_for(judged)
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            render_reason(judged, reaction is not None),
            t.now,
            detail={
                "scorer": model,
                "schema_hash": schema_hash(),
                "inputs_hash": inputs_hash(prompt),
                "scores": {"kind": judged.kind, "confidence": judged.confidence},
                "threshold": REACT_THRESHOLD,
            },
        )
    )
    return reaction


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str | Reaction:
    store, talker, prefix, rel = c.store, c.talker, c.prefix, c.rel
    now = now or datetime.now(UTC)
    turn = TurnId(_id())
    prior = store.history_before(rel, now, HISTORY_LIMIT)
    history = to_messages(prior)
    user = Utterance(
        UtteranceId(_id()), rel, session, turn, Speaker.USER, text, Frame.REAL, channel, now
    )
    store.append_utterance(user)
    support = store.last_support(rel)
    view_state = store.view_state(rel)
    views = card_views(store.self_beliefs(rel), view_state)
    card = build_card(store.user_beliefs(rel), support, now, views=views)
    clock = volatile_line(now, prior[-1].at if prior else None)
    volatile = (
        f"{clock}\n{render(card, now.astimezone().tzinfo or UTC)}" if not card.empty else clock
    )
    request = build_request(prefix, history, text, volatile)
    store.save_prefix(prefix)
    # The talker starts at once. The ack judge runs beside it, so a message that needs a reply
    # pays no extra wait, and a confident acknowledgement cancels the call.
    talk = asyncio.ensure_future(talker.reply(request))
    try:
        reaction = await _ack_reaction(c, _Turn(session, turn, now, prior, text))
    except BaseException:
        talk.cancel()
        raise
    if reaction is not None:
        talk.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await talk
        log.info("turn %s | ack -> %s\n  you: %s", turn[:8], reaction.emoji, text)
        return reaction
    reply = await talk
    store.record_turn(
        TurnRecord(
            turn, rel, session, prefix.sha256, volatile, request_sha256(request), reply.model, now
        )
    )
    _CardLog(store, rel, session, turn, now, {b.id: why(b, view_state) for b in views}).write(card)
    log.info(
        "turn %s | %dms in=%d cache_read=%d cache_write=%d\n  you: %s\n  it:  %s",
        turn[:8],
        reply.latency_ms,
        reply.input_tokens,
        reply.cache_read_tokens,
        reply.cache_write_tokens,
        text,
        reply.text or "(no reply)",
    )
    replied_at = now + timedelta(milliseconds=max(reply.latency_ms, 1))
    if not reply.text:
        store.append_decision(
            Decision(
                DecisionId(_id()),
                rel,
                session,
                turn,
                TraceId(turn),
                DecisionKind.DO_NOTHING,
                "model returned no text",
                replied_at,
            )
        )
        return ""
    out = Utterance(
        UtteranceId(_id()),
        rel,
        session,
        turn,
        Speaker.COMPANION,
        reply.text,
        Frame.REAL,
        channel,
        replied_at,
    )
    store.append_utterance(out)
    store.append_decision(
        Decision(
            DecisionId(_id()),
            rel,
            session,
            turn,
            TraceId(turn),
            DecisionKind.POLICY,
            "replied: every user message gets a reply in v1",
            replied_at,
            detail={
                "latency_ms": reply.latency_ms,
                "input_tokens": reply.input_tokens,
                "cache_read_tokens": reply.cache_read_tokens,
                "cache_write_tokens": reply.cache_write_tokens,
            },
        )
    )
    return reply.text
