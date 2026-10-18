"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from companion.core.ack import PROMPT as ACK_PROMPT
from companion.core.ack import (
    REACT_THRESHOLD,
    ReactAndReply,
    Reaction,
    inputs_hash,
    is_candidate,
    reaction_for,
    render_reason,
    schema_hash,
)
from companion.core.card import Card, build_card, render
from companion.core.clock import now_line, utc_now
from companion.core.extractor import Extractor
from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import PROMPT as FRAMES_PROMPT
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
from companion.core.freshness import HORIZON_DAYS, when_phrase
from companion.core.habits import habit_note
from companion.core.history import HISTORY_LIMIT, to_messages
from companion.core.length import length_note
from companion.core.listening import PROMPT as LISTEN_PROMPT
from companion.core.listening import SERIOUS, listening_note
from companion.core.listening import Judgement as ListenJudgement
from companion.core.listening import render_reason as render_listening
from companion.core.moves import PROMPT as HABITS_PROMPT
from companion.core.moves import replies_to_read
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import TalkerRequest, build_request, request_sha256
from companion.core.react import PROMPT as REACT_PROMPT
from companion.core.react import Judgement as ReactJudgement
from companion.core.react import decide as decide_reaction
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
from companion.core.views import ViewState, card_views, why
from companion.loops.ack import judge
from companion.loops.frames import inputs_hash as frames_inputs_hash
from companion.loops.frames import judge_frame
from companion.loops.frames import schema_hash as frames_schema_hash
from companion.loops.listen import judge_listening
from companion.loops.moves import HabitMemory, find_habits
from companion.loops.react import judge_reaction
from companion.loops.spendcap import NOTICE, first_notice_today, over_cap
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
        last = when_phrase(card.aged[b.id].last_supported, card.now)
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
    habits: HabitMemory = field(default_factory=HabitMemory)
    scene_talker: Talker | None = None  # replies while a pretend scene is in progress
    daily_cap_usd: float | None = None  # nothing paid runs once today's spend reaches this
    listen: bool = True  # ask how serious a message is before the reply

    async def handle(
        self, session: SessionId, text: str, channel: str, now: datetime | None = None
    ) -> str | Reaction | ReactAndReply:
        now = now or utc_now()
        capped = _stopped_by_cap(self, session, text, channel, now)
        if capped is not None:
            return capped
        return await _handle_turn(self, session, text, channel, now)


@dataclass(frozen=True, slots=True)
class _Turn:
    session: SessionId
    turn: TurnId
    now: datetime
    prior: list[Utterance]
    text: str
    started: float = field(default_factory=time.perf_counter)


def _mark(t: _Turn, what: str) -> None:
    """One DEBUG line per stage of a turn, with the milliseconds since the turn began."""
    log.debug("turn %s +%dms %s", t.turn[:8], (time.perf_counter() - t.started) * 1000, what)


def _mark_start(t: _Turn, in_scene: Frame, card: Card, card_text: str) -> None:
    _mark(
        t,
        f"start: {len(t.prior)} history messages, scene={in_scene.value},"
        f" card {len(card_text)} chars ({len(card.usable)} usable, {len(card.held)} held,"
        f" {len(card.older)} older, {len(card.dropped)} dropped, {len(card.views)} views),"
        f" text {len(t.text)} chars",
    )


async def _await_beside(
    t: _Turn,
    talk: asyncio.Future[Reply],
    framing: asyncio.Future[Any] | None,
    feeling: asyncio.Future[Any] | None,
) -> tuple[Reply, Any, Any]:
    """The reply, then the frame and reaction judgements that ran beside it, marking each."""
    reply = await talk
    _mark_reply(t, reply)
    outcome = await framing if framing is not None else None
    if framing is not None:
        _mark(t, "frame judge done")
    felt = await feeling if feeling is not None else None
    if feeling is not None:
        _mark(t, "reaction judge done")
    return reply, outcome, felt


def _mark_reply(t: _Turn, reply: Reply) -> None:
    _mark(
        t,
        f"talker done: {reply.model} {reply.latency_ms}ms in={reply.input_tokens}"
        f" cache_read={reply.cache_read_tokens} cost=${reply.cost_usd:.5f},"
        f" {len(reply.text.split())} words",
    )


async def _ack_reaction(c: Conversation, t: _Turn) -> Reaction | None:
    """A reaction if this short message only acknowledges. Logs every judgement it makes."""
    if c.judge is None or not is_candidate(t.text, t.prior, after_serious=_after_serious(c, t)):
        _mark(t, "ack judge skipped: not a candidate for a reaction")
        return None
    outcome = await judge(c.judge, t.prior, t.text)
    if outcome is None:
        _mark(t, "ack judge gave no answer; replying")
        return None
    judged, model, prompt = outcome
    reaction = reaction_for(judged)
    _mark(
        t, f"ack judged {judged.kind} {judged.confidence:.2f} -> {'react' if reaction else 'reply'}"
    )
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
                "prompt": ACK_PROMPT.ref,
                "schema_hash": schema_hash(),
                "inputs_hash": inputs_hash(prompt),
                "scores": {"kind": judged.kind, "confidence": judged.confidence},
                "threshold": REACT_THRESHOLD,
            },
        )
    )
    return reaction


def _after_serious(c: Conversation, t: _Turn) -> bool:
    """Whether the listening judge found their previous message serious (severity 2 or more)."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id):
        labels = d.detail.get("labels") if d.detail else None
        severity = labels.get("severity") if isinstance(labels, dict) else None
        if isinstance(severity, int) and not isinstance(severity, bool) and severity >= SERIOUS:
            return True
    return False


def _react_alongside(
    c: Conversation, t: _Turn, felt: tuple[ReactJudgement, str, str] | None
) -> Reaction | None:
    """A reaction to send with the reply, if the message calls for one. Logs the judgement."""
    if felt is None:
        return None
    judged, model, prompt = felt
    decision = decide_reaction(judged, c.store.turns_since_reaction(c.rel))
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            decision.reason,
            t.now,
            detail={
                "scorer": model,
                "prompt": REACT_PROMPT.ref,
                "inputs_hash": inputs_hash(prompt),
                "scores": {"tone": judged.tone, "confidence": judged.confidence},
            },
        )
    )
    return decision.reaction


def _notes(
    c: Conversation, prior: list[Utterance], in_scene: Frame, text: str, heard: _Heard | None
) -> list[str]:
    """What it should know about its own habits, a scene in progress and how long to answer.
    These go in the system block with the memory card: in a user message the model read them as
    something they said. A scene gets no length note, since scenes run long on purpose, and nor
    does a serious message, whose length the listening note sets."""
    serious = heard is not None and heard[0].severity >= SERIOUS
    size = length_note(text, serious=serious) if in_scene is Frame.REAL else None
    notes = [habit_note(prior), c.habits.note(), scene_note(in_scene), size]
    return [n for n in notes if n is not None]


def _check_habits(c: Conversation, t: _Turn, sent: str) -> None:
    """After the reply is out, read the last few replies in the background for habits."""
    if c.judge is None:
        return
    replies = replies_to_read(t.prior, sent)
    if not replies:
        return

    async def look() -> list[str] | None:
        found = await find_habits(c.judge, replies)  # type: ignore[arg-type]
        if found is None:
            return None
        habits, model, prompt = found
        detail: dict[str, Json] = {
            "scorer": model,
            "prompt": HABITS_PROMPT.ref,
            "inputs_hash": inputs_hash(prompt),
            "habits": list[Json](habits),
        }
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                c.rel,
                t.session,
                t.turn,
                TraceId(t.turn),
                DecisionKind.POLICY,
                f"habit check: {len(habits)} habits found in the last {len(replies)} replies",
                t.now,
                detail=detail,
            )
        )
        return habits

    c.habits.start(look())


def _stopped_by_cap(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime
) -> str | None:
    """At the daily cap the user's message is kept and nothing paid runs, and they are told once.

    None means under the cap and the turn goes ahead. An empty string means send nothing."""
    spent = over_cap(c.store, c.rel, c.daily_cap_usd, now)
    if spent is None:
        return None
    turn = TurnId(_id())
    t = _Turn(session, turn, now, [], text)
    _store_user(c, t, channel, Frame.REAL)
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            session,
            turn,
            TraceId(turn),
            DecisionKind.POLICY,
            f"daily spend cap reached: ${spent:.2f} of ${c.daily_cap_usd or 0:.2f}, no reply",
            now,
        )
    )
    return NOTICE if first_notice_today(c.store, c.rel, now) else ""


def _pick_talker(c: Conversation, t: _Turn, in_scene: Frame) -> Talker:
    """The scene talker while a pretend scene is in progress, the everyday talker otherwise.

    The frame is the one the previous turn left, so the first message of a scene is answered by
    the everyday talker and the next ones by the scene talker. The choice is logged.
    """
    if c.scene_talker is None or in_scene is not Frame.PLAY:
        return c.talker
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            "replied with the scene talker: a pretend scene is in progress",
            t.now,
        )
    )
    return c.scene_talker


def _start_beside(
    c: Conversation, t: _Turn, request: TalkerRequest, in_scene: Frame
) -> tuple[
    asyncio.Future[Reply],
    asyncio.Future[tuple[Judgement, str, str] | None] | None,
    asyncio.Future[tuple[ReactJudgement, str, str] | None] | None,
]:
    """Start the reply, and beside it the frame judge and the reaction judge, so neither adds a
    wait. A confident acknowledgement cancels all of them."""
    talk = asyncio.ensure_future(_pick_talker(c, t, in_scene).reply(request))
    if c.judge is None:
        return talk, None, None
    framing = (
        asyncio.ensure_future(judge_frame(c.judge, t.prior, t.text))
        if needs_judge(t.text, t.prior)
        else None
    )
    return talk, framing, asyncio.ensure_future(judge_reaction(c.judge, t.prior, t.text))


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


async def _stop(*tasks: asyncio.Future[Any] | None) -> None:
    """Cancel whatever is still running beside the reply."""
    for task in tasks:
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


def _log_frame(
    c: Conversation, t: _Turn, outcome: tuple[Judgement, str, str] | None, stored: Frame
) -> None:
    """Record every frame judgement and what was stored, with the reason built by code."""
    judged = outcome[0] if outcome else None
    detail: dict[str, Json] = {"stored": stored.value}
    if outcome is not None:
        detail |= {
            "scorer": outcome[1],
            "prompt": FRAMES_PROMPT.ref,
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
    _check_habits(c, t, reply.text)
    return reply.text


_Heard = tuple[ListenJudgement, str, str]


@dataclass(frozen=True, slots=True)
class _Assembled:
    """What one turn sends and what it needs to record afterwards."""

    request: TalkerRequest
    card_text: str
    card: Card
    views: Sequence[Belief]
    view_state: ViewState


async def _listening(c: Conversation, t: _Turn, in_scene: Frame) -> _Heard | None:
    """How serious the message is and what they are doing. Not asked in a scene."""
    if c.judge is None or not c.listen or in_scene is not Frame.REAL:
        return None
    return await judge_listening(c.judge, t.prior, t.text)


def _listening_note(c: Conversation, t: _Turn, heard: _Heard | None) -> str | None:
    """The line for the system block, with the decision logged from the labels."""
    if heard is None:
        return None
    judged, model, prompt = heard
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    note = listening_note(judged, replies)
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            render_listening(judged, note),
            t.now,
            detail={
                "scorer": model,
                "prompt": LISTEN_PROMPT.ref,
                "inputs_hash": inputs_hash(prompt),
                "labels": {
                    "severity": judged.severity,
                    "stance": judged.stance,
                    "vague": judged.vague,
                },
            },
        )
    )
    return note


def _assemble(c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None) -> _Assembled:
    store, now = c.store, t.now
    view_state = store.view_state(c.rel)
    views = card_views(store.self_beliefs(c.rel), view_state)
    assertable = [b for b in store.user_beliefs(c.rel) if is_assertable(b)]
    card = build_card(assertable, store.last_support(c.rel), now, views=views)
    shown = [] if card.empty else [render(card, now.astimezone().tzinfo or UTC)]
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    clock = now_line(now, theirs[-1].at if theirs else None)
    notes = _notes(c, t.prior, in_scene, t.text, heard)
    listening = _listening_note(c, t, heard)
    notes += [listening] if listening is not None else []
    card_text = "\n".join([clock, *shown, *notes])
    request = build_request(c.prefix, to_messages(t.prior), t.text, "", card_text)
    store.save_prefix(c.prefix)
    _mark_start(t, in_scene, card, card_text)
    return _Assembled(request, card_text, card, views, view_state)


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str | Reaction | ReactAndReply:
    store, prefix, rel = c.store, c.prefix, c.rel
    now = now or utc_now()
    turn = TurnId(_id())
    prior = store.history_before(rel, now, HISTORY_LIMIT)
    t = _Turn(session, turn, now, prior, text)
    in_scene = scene_frame(prior)
    listening = asyncio.ensure_future(_listening(c, t, in_scene))
    heard: _Heard | None = None
    try:
        reaction = await _ack_reaction(c, t)
        if reaction is None:
            heard = await listening
    except BaseException:
        await _stop(listening)
        _store_user(c, t, channel, Frame.REAL)
        raise
    if reaction is not None:
        await _stop(listening)
        _store_user(c, t, channel, in_scene)
        _mark(t, "done: reaction only")
        log.info("turn %s | ack -> %s\n  you: %s", turn[:8], reaction.emoji, text)
        return reaction
    asm = _assemble(c, t, in_scene, heard)
    request, card_text, card, views, view_state = (
        asm.request,
        asm.card_text,
        asm.card,
        asm.views,
        asm.view_state,
    )
    talk, framing, feeling = _start_beside(c, t, request, in_scene)
    try:
        reply, outcome, felt = await _await_beside(t, talk, framing, feeling)
    except BaseException:
        await _stop(talk, framing, feeling)
        _store_user(c, t, channel, Frame.REAL)
        raise
    user_frame = frame_resolve(outcome[0] if outcome else None, fallback=in_scene)
    _store_user(c, t, channel, user_frame)
    if framing is not None:
        _log_frame(c, t, outcome, user_frame)
    store.record_turn(
        TurnRecord(
            turn,
            rel,
            session,
            prefix.sha256,
            "",
            request_sha256(request),
            reply.model,
            now,
            card_text,
        )
    )
    _CardLog(store, rel, session, turn, now, {b.id: why(b, view_state) for b in views}).write(card)
    log.info(
        "turn %s | %s %dms in=%d cache_read=%d cache_write=%d%s\n  you: %s\n  it:  %s",
        turn[:8],
        reply.model,
        reply.latency_ms,
        reply.input_tokens,
        reply.cache_read_tokens,
        reply.cache_write_tokens,
        f" | frame={user_frame.value}" if user_frame is not Frame.REAL else "",
        text,
        reply.text or "(no reply)",
    )
    sent = _persist_reply(c, t, reply, user_frame, channel)
    reacted = _react_alongside(c, t, felt)
    _mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to Telegram")
    return ReactAndReply(reacted, sent) if reacted is not None else sent
