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
from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import (
    Judgement,
    companion_frame,
    is_assertable,
    needs_judge,
    scene_frame,
    scene_note,
)
from companion.core.frames import render_reason as frame_reason
from companion.core.frames import resolve as frame_resolve
from companion.core.freshness import HORIZON_DAYS, age_phrase
from companion.core.history import HISTORY_LIMIT, to_messages
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import build_request, request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Reply, Talker
from companion.core.types import (
    Belief,
    BeliefId,
    Decision,
    DecisionId,
    DecisionKind,
    Frame,
    Json,
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
from companion.loops.frames import inputs_hash as frames_inputs_hash
from companion.loops.frames import judge_frame
from companion.loops.frames import schema_hash as frames_schema_hash
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


def _store_user(c: Conversation, t: _Turn, channel: str, frame: Frame) -> None:
    c.store.append_utterance(
        Utterance(
            UtteranceId(_id()),
            c.rel,
            t.session,
            t.turn,
            Speaker.USER,
            t.text,
            frame,
            channel,
            t.now,
        )
    )


async def _stop(
    talk: asyncio.Future[Reply], framing: asyncio.Future[tuple[Judgement, str, str] | None] | None
) -> None:
    """Cancel whatever is still running beside the reply."""
    talk.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await talk
    if framing is not None:
        framing.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await framing


def _log_frame(
    c: Conversation, t: _Turn, outcome: tuple[Judgement, str, str] | None, stored: Frame
) -> None:
    """Record every frame judgement and what was stored, with the reason built by code."""
    judged = outcome[0] if outcome else None
    detail: dict[str, Json] = {"stored": stored.value}
    if outcome is not None:
        detail |= {
            "scorer": outcome[1],
            "schema_hash": frames_schema_hash(),
            "inputs_hash": frames_inputs_hash(outcome[2]),
            "scores": {"frame": outcome[0].frame.value, "confidence": outcome[0].confidence},
            "threshold": FRAME_MIN_CONFIDENCE,
        }
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            frame_reason(judged, stored),
            t.now,
            detail=detail,
        )
    )


def _persist_reply(c: Conversation, t: _Turn, reply: Reply, user_frame: Frame, channel: str) -> str:
    """Store the companion's reply and the decision that sent it. Returns what to send."""
    replied_at = t.now + timedelta(milliseconds=max(reply.latency_ms, 1))
    ids = (c.rel, t.session, t.turn)
    if not reply.text:
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                *ids,
                TraceId(t.turn),
                DecisionKind.DO_NOTHING,
                "model returned no text",
                replied_at,
            )
        )
        return ""
    c.store.append_utterance(
        Utterance(
            UtteranceId(_id()),
            *ids,
            Speaker.COMPANION,
            reply.text,
            companion_frame(user_frame),
            channel,
            replied_at,
        )
    )
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            *ids,
            TraceId(t.turn),
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


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str | Reaction:
    store, talker, prefix, rel = c.store, c.talker, c.prefix, c.rel
    now = now or datetime.now(UTC)
    turn = TurnId(_id())
    prior = store.history_before(rel, now, HISTORY_LIMIT)
    history = to_messages(prior)
    t = _Turn(session, turn, now, prior, text)
    in_scene = scene_frame(prior)
    support = store.last_support(rel)
    view_state = store.view_state(rel)
    views = card_views(store.self_beliefs(rel), view_state)
    assertable = [b for b in store.user_beliefs(rel) if is_assertable(b)]
    card = build_card(assertable, support, now, views=views)
    clock = volatile_line(now, prior[-1].at if prior else None)
    parts = [clock]
    if (note := scene_note(in_scene)) is not None:
        parts.append(note)
    if not card.empty:
        parts.append(render(card, now.astimezone().tzinfo or UTC))
    volatile = "\n".join(parts)
    request = build_request(prefix, history, text, volatile)
    store.save_prefix(prefix)
    # The talker starts at once. The ack judge and the frame judge run beside it, so a message that
    # needs a reply pays no extra wait, and a confident acknowledgement cancels the call.
    talk = asyncio.ensure_future(talker.reply(request))
    framing = (
        asyncio.ensure_future(judge_frame(c.judge, prior, text))
        if c.judge is not None and needs_judge(text, prior)
        else None
    )
    try:
        reaction = await _ack_reaction(c, t)
    except BaseException:
        await _stop(talk, framing)
        _store_user(c, t, channel, Frame.REAL)
        raise
    if reaction is not None:
        await _stop(talk, framing)
        _store_user(c, t, channel, in_scene)
        log.info("turn %s | ack -> %s\n  you: %s", turn[:8], reaction.emoji, text)
        return reaction
    try:
        reply = await talk
        outcome = await framing if framing is not None else None
    except BaseException:
        await _stop(talk, framing)
        _store_user(c, t, channel, Frame.REAL)
        raise
    user_frame = frame_resolve(outcome[0] if outcome else None, fallback=in_scene)
    _store_user(c, t, channel, user_frame)
    if framing is not None:
        _log_frame(c, t, outcome, user_frame)
    store.record_turn(
        TurnRecord(
            turn, rel, session, prefix.sha256, volatile, request_sha256(request), reply.model, now
        )
    )
    _CardLog(store, rel, session, turn, now, {b.id: why(b, view_state) for b in views}).write(card)
    log.info(
        "turn %s | %dms in=%d cache_read=%d cache_write=%d%s\n  you: %s\n  it:  %s",
        turn[:8],
        reply.latency_ms,
        reply.input_tokens,
        reply.cache_read_tokens,
        reply.cache_write_tokens,
        f" | frame={user_frame.value}" if user_frame is not Frame.REAL else "",
        text,
        reply.text or "(no reply)",
    )
    return _persist_reply(c, t, reply, user_frame, channel)
