"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import Message, build_request, request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Talker
from companion.core.types import (
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

HISTORY_LIMIT = 40


def _id() -> str:
    return uuid.uuid4().hex


def _volatile(now: datetime) -> str:
    return f"[{now.astimezone().strftime('%A %H:%M')}]"


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
    prior = store.session_utterances(rel, session)[-HISTORY_LIMIT:]
    history = [Message("user" if u.speaker is Speaker.USER else "assistant", u.text) for u in prior]
    user = Utterance(
        UtteranceId(_id()), rel, session, turn, Speaker.USER, text, Frame.REAL, channel, now
    )
    store.append_utterance(user)
    volatile = _volatile(now)
    request = build_request(prefix, history, text, volatile)
    store.save_prefix(prefix)
    reply = await talker.reply(request)
    store.record_turn(
        TurnRecord(
            turn, rel, session, prefix.sha256, volatile, request_sha256(request), reply.model, now
        )
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
