"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from companion.core.card import Card, build_card, render
from companion.core.clock import volatile_line
from companion.core.history import HISTORY_LIMIT, to_messages
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import build_request, request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Talker
from companion.core.types import (
    Belief,
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

    def write(self, card: Card) -> None:
        for b in card.usable:
            self._one(DecisionKind.SURFACE, b, "in the card")
        for b in card.held:
            self._one(
                DecisionKind.WITHHOLD, b, f"sensitivity {b.sensitivity}: known, held for listening"
            )

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

    async def handle(
        self, session: SessionId, text: str, channel: str, now: datetime | None = None
    ) -> str:
        return await _handle_turn(self, session, text, channel, now)


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str:
    store, talker, prefix, rel = c.store, c.talker, c.prefix, c.rel
    now = now or datetime.now(UTC)
    turn = TurnId(_id())
    prior = store.history_before(rel, now, HISTORY_LIMIT)
    history = to_messages(prior)
    user = Utterance(
        UtteranceId(_id()), rel, session, turn, Speaker.USER, text, Frame.REAL, channel, now
    )
    store.append_utterance(user)
    card = build_card(store.current_beliefs(rel))
    clock = volatile_line(now, prior[-1].at if prior else None)
    volatile = f"{clock}\n{render(card)}" if not card.empty else clock
    request = build_request(prefix, history, text, volatile)
    store.save_prefix(prefix)
    reply = await talker.reply(request)
    store.record_turn(
        TurnRecord(
            turn, rel, session, prefix.sha256, volatile, request_sha256(request), reply.model, now
        )
    )
    _CardLog(store, rel, session, turn, now).write(card)
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
