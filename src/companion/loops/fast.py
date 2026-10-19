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
from companion.core.address import KEY as ADDRESS_KEY
from companion.core.address import address_note
from companion.core.basics import ASK_EVERY as ASK_NAME_EVERY
from companion.core.basics import ASKED as ASKED_NAME
from companion.core.basics import NAME_CAPTURE, ask_name, asked_for_name, knows_name, name_belief
from companion.core.card import Card, build_card, render
from companion.core.clock import local_zone, now_line, utc_now
from companion.core.extractor import Extractor, from_fallback
from companion.core.floor import HOLD_NOTE, INTIMATE_CHECK
from companion.core.floor import Talker as RouteTalker
from companion.core.floor import choose as choose_route
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
from companion.core.knowing import MAP_EVERY, WOULD_ASK, pick_gap
from companion.core.length import LengthTarget, length_target
from companion.core.listening import PROMPT as LISTEN_PROMPT
from companion.core.listening import SERIOUS, listening_note, repair_note, rude_note
from companion.core.listening import Judgement as ListenJudgement
from companion.core.listening import render_reason as render_listening
from companion.core.mood import PARAMS_VERSION as MOOD_PARAMS
from companion.core.mood import WINDOW as MOOD_WINDOW
from companion.core.mood import Effect as MoodEffect
from companion.core.mood import Said, chat_minutes, effects_for, held_because, inputs_for, mood_at
from companion.core.mood import line as mood_line
from companion.core.mood import reason as mood_reason
from companion.core.moves import PROMPT as HABITS_PROMPT
from companion.core.moves import replies_to_read
from companion.core.openloops import LoopState, loop_note, loop_note_ref, pick_note
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import TalkerRequest, build_request, request_sha256
from companion.core.quip import PROMPT as QUIP_PROMPT
from companion.core.react import PROMPT as REACT_PROMPT
from companion.core.react import Judgement as ReactJudgement
from companion.core.react import decide as decide_reaction
from companion.core.recall import PROMPT as RECALL_PROMPT
from companion.core.recall import recall_note
from companion.core.recheck import QUIP, code_checks
from companion.core.recheck import eligible as recheck_eligible
from companion.core.relevance import SHADOW as RELEVANCE_SHADOW
from companion.core.relevance import Embedder
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
from companion.loops.basics import judge_name
from companion.loops.floor import judge_intimate
from companion.loops.frames import inputs_hash as frames_inputs_hash
from companion.loops.frames import judge_frame
from companion.loops.frames import schema_hash as frames_schema_hash
from companion.loops.listen import judge_listening
from companion.loops.moves import HabitMemory, find_habits
from companion.loops.quip import judge_quip
from companion.loops.react import judge_reaction
from companion.loops.recall import Recalled, look_up
from companion.loops.relevance import shadow as relevance_shadow
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
        if card.kept_back:
            self.store.append_decision(
                Decision(
                    DecisionId(_id()),
                    self.rel,
                    self.session,
                    self.turn,
                    TraceId(self.turn),
                    DecisionKind.POLICY,
                    f"card: {len(card.kept_back)} held beliefs left out, the turn is casual",
                    self.at,
                    detail={"kept_back": [b.id for b in card.kept_back]},
                )
            )
        if card.crowded:
            self.store.append_decision(
                Decision(
                    DecisionId(_id()),
                    self.rel,
                    self.session,
                    self.turn,
                    TraceId(self.turn),
                    DecisionKind.POLICY,
                    f"card: {len(card.crowded)} current beliefs crowded out, it holds "
                    f"{len(card.usable) + len(card.held)}",
                    self.at,
                    detail={"crowded": [b.id for b in card.crowded]},
                )
            )
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
    roleplay_talker: Talker | None = None  # replies while a pretend scene is in progress
    daily_cap_usd: float | None = None  # nothing paid runs once today's spend reaches this
    listen: bool = True  # ask how serious a message is before the reply
    mood: str = "off"  # off, shadow (worked out and logged, never shown) or on (ADR 0016)
    resample: bool = False  # draw one fresh reply when the first fails a check (core/recheck.py)
    route_intimate: bool = False  # intimate talk may go to the roleplay talker (ADR 0017)
    roleplay_prefix: Prefix | None = (
        None  # the roleplay talker's system prompt, with the sheet's scene section
    )
    embedder: Embedder | None = None  # the relevance look-up runs in shadow when set
    embed_model: str = ""

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
    c: Conversation, prior: list[Utterance], in_scene: Frame, size: LengthTarget | None
) -> list[str]:
    """What it should know about its own habits, a scene in progress and how long to answer.
    These go in the system block with the memory card: in a user message the model read them as
    something they said."""
    notes = [habit_note(prior), c.habits.note(), scene_note(in_scene), size.note if size else None]
    return [n for n in notes if n is not None]


def _length(
    c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None
) -> LengthTarget | None:
    """The one length target for this turn, logged with the reason code wrote for it."""
    severity = heard[0].severity if heard is not None else None
    size = length_target(
        t.text, severity=severity, in_scene=in_scene is not Frame.REAL, seed=str(t.turn)
    )
    reason = f"length: under about {size.words} words, {size.why}" if size else "length: no cap"
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            reason,
            t.now,
            detail={"words": size.words if size else None, "severity": severity},
        )
    )
    return size


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


async def _route(
    c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None
) -> tuple[Talker, bool, _Heard | None]:
    """The talker for this turn (ADR 0017): the roleplay talker for a pretend scene, or for intimate
    talk when COMPANION_ROUTE_INTIMATE allows it, unless the floor keeps it on the everyday talker.
    Logged when it is anything but the plain everyday choice.

    The listening judge does not run in a scene, so a scene turn is read here, for routing only.
    The frame is the one the previous turn left, so the first message of a scene is answered by
    the everyday talker and the next ones by the roleplay talker. Returns that read too, so a
    scene turn can still look something up when they say it forgot.
    """
    if c.roleplay_talker is None:
        return c.talker, False, heard
    in_play = in_scene is Frame.PLAY
    read = heard
    if read is None and in_play and c.judge is not None:
        _mark(t, "floor: reading the scene turn")
        read = await judge_listening(c.judge, t.prior, t.text)  # for routing only, no note
    route = choose_route(
        in_play=in_play,
        intimate=read is not None and read[0].intimate,
        allow_intimate=c.route_intimate,
        judged_age_coded=read[0].age_coded
        if read is not None and not from_fallback(read[1])
        else None,
    )
    if route.reason is not None:
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                c.rel,
                t.session,
                t.turn,
                TraceId(t.turn),
                DecisionKind.POLICY,
                route.reason,
                t.now,
            )
        )
    talker = c.roleplay_talker if route.talker is RouteTalker.ROLEPLAY else c.talker
    return talker, route.held, read


def _start_beside(
    c: Conversation, t: _Turn, request: TalkerRequest, talker: Talker
) -> tuple[
    asyncio.Future[Reply],
    asyncio.Future[tuple[Judgement, str, str] | None] | None,
    asyncio.Future[tuple[ReactJudgement, str, str] | None] | None,
]:
    """Start the reply, and beside it the frame judge and the reaction judge, so neither adds a
    wait. A confident acknowledgement cancels all of them."""
    talk = asyncio.ensure_future(talker.reply(request))
    if c.judge is None:
        return talk, None, None
    framing = (
        asyncio.ensure_future(judge_frame(c.judge, t.prior, t.text))
        if needs_judge(t.text, t.prior)
        else None
    )
    return talk, framing, asyncio.ensure_future(judge_reaction(c.judge, t.prior, t.text))


async def _recheck(  # noqa: PLR0913, PLR0917
    c: Conversation,
    t: _Turn,
    request: TalkerRequest,
    reply: Reply,
    heard: _Heard | None,
    in_scene: Frame,
    talker: Talker,
) -> Reply:
    """The reply to send: the first, or one fresh draw when the first fails a check. On an ordinary
    turn every check runs and the result is logged; in a scene only the code checks run, since play
    is expected there, and only a resample is logged."""
    severity = heard[0].severity if heard is not None else None
    scene = talker is c.roleplay_talker or in_scene is not Frame.REAL
    if not c.resample or not reply.text.strip():
        return reply
    if not scene and not recheck_eligible(severity=severity, in_scene=False, reply=reply.text):
        return reply
    failed = code_checks(reply.text, t.text)
    if scene and not failed:
        return reply  # in a scene only the code checks run, and a passing reply is not logged
    detail: dict[str, Json] = {}
    if not failed and c.judge is not None:
        judged = await judge_quip(c.judge, t.text, reply.text)
        if judged is not None:
            detail = {"scorer": judged[1], "prompt": QUIP_PROMPT.ref}
            if judged[0]:
                failed.append(QUIP)
    _mark(t, f"recheck: {', '.join(failed) or 'passed'}")
    again = None
    if failed:
        again = await talker.reply(request)
        _mark_reply(t, again)
        detail |= {"discarded": reply.text, "checks": list[Json](failed)}
    reason = f"resampled: {', '.join(failed)}" if failed else "kept: the reply passed its checks"
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            reason,
            t.now,
            detail=detail or None,
        )
    )
    return again if again is not None and again.text else reply


async def _checked(  # noqa: PLR0913, PLR0917
    c: Conversation,
    t: _Turn,
    request: TalkerRequest,
    reply: Reply,
    heard: _Heard | None,
    in_scene: Frame,
    talker: Talker,
    *,
    held: bool,
) -> Reply:
    """The reply after its checks: the habit checks on an ordinary turn, the floor's on a held
    one."""
    reply = await _recheck(c, t, request, reply, heard, in_scene, talker)
    return await _hold_check(c, t, request, reply, talker) if held else reply


async def _hold_check(
    c: Conversation, t: _Turn, request: TalkerRequest, reply: Reply, talker: Talker
) -> Reply:
    """On a turn the floor held, the reply must not be intimate (ADR 0017). An intimate or unread
    reply is drawn again with the same request, then once more with only their last message in
    view, so the history that pulled it along is gone. If all three read as intimate, nothing is
    sent this turn. Every step is logged with what was discarded; no reply is written by code."""
    if c.judge is None:
        return reply
    lean = TalkerRequest(prefix=request.prefix, messages=request.messages[-1:], card=request.card)
    tries = (request, lean)
    discarded: list[Json] = []
    for attempt in range(len(tries) + 1):
        if await judge_intimate(c.judge, reply.text) is False:
            break
        discarded.append(reply.text)
        if attempt < len(tries):
            reply = await talker.reply(tries[attempt])
            _mark_reply(t, reply)
    else:
        reply = Reply(text="", model=reply.model, latency_ms=reply.latency_ms)
    if discarded:
        sent = ["a second reply", "a reply drawn with only their last message", "nothing"]
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                c.rel,
                t.session,
                t.turn,
                TraceId(t.turn),
                DecisionKind.POLICY,
                f"floor: a reply on a held turn read as intimate, sent {sent[len(discarded) - 1]}",
                t.now,
                detail={"discarded": discarded, "prompt": INTIMATE_CHECK.ref},
            )
        )
    return reply


def _store_user(c: Conversation, t: _Turn, channel: str, frame: Frame) -> Utterance:
    said = Utterance(
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
    c.store.append_utterance(said)
    return said


def _with_reaction(
    c: Conversation, t: _Turn, felt: tuple[ReactJudgement, str, str] | None, sent: str
) -> str | ReactAndReply:
    reacted = _react_alongside(c, t, felt)
    _mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to Telegram")
    return ReactAndReply(reacted, sent) if reacted is not None else sent


async def _capture_name(c: Conversation, t: _Turn, said: Utterance) -> None:
    """When its last message asked what to call them, read their answer and remember the name,
    quoting their own words. Logged either way."""
    asked = next((u.text for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), "")
    if c.judge is None or not asked_for_name(asked):
        return
    if knows_name(c.store.user_beliefs(c.rel)):
        return
    name = await judge_name(c.judge, asked, t.text)
    reason = "basics: no name in their answer"
    if name is not None:
        c.store.insert_belief(name_belief(said, name, _id(), t.now))
        reason = f"basics: remembered what to call them ({name})"
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            reason,
            t.now,
            detail={"prompt": NAME_CAPTURE.ref},
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
    mood: Sequence[
        MoodEffect
    ] = ()  # written once their message is stored, so a dropped turn adds none


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
                    "rude": judged.rude,
                },
            },
        )
    )
    return note


async def _recall(c: Conversation, t: _Turn, heard: _Heard | None) -> Recalled | None:
    """When they asked it to remember something, look it up across all of memory and log it."""
    if c.judge is None or heard is None or not heard[0].recall or not heard[0].topic:
        return None
    _mark(t, f"recall look-up: {heard[0].topic!r}")
    recalled = await look_up(c.judge, c.store.user_beliefs(c.rel), heard[0].topic)
    found = recalled.picked if recalled is not None else ()
    reason = f"recall: they asked about {heard[0].topic!r}; " + (
        f"{len(found)} found" if recalled is not None else "the look-up failed"
    )
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            reason,
            t.now,
            detail={
                "topic": heard[0].topic,
                "picked": [b.id for b in found],
                "searched": recalled.searched if recalled is not None else 0,
                "scorer": recalled.model if recalled is not None else "",
                "prompt": RECALL_PROMPT.ref,
            },
        )
    )
    return recalled


def _mood(
    c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None
) -> tuple[str | None, list[MoodEffect]]:
    """The mood line for the system block when the mood is on, and what this message adds to it.
    The decision is logged in shadow mode too, so the replay and the live log can be compared."""
    if c.mood == "off":
        return None, []
    zone = local_zone()
    severity = heard[0].severity if heard is not None else None
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    earlier = c.store.said_since(c.rel, theirs[-1].at)[:1] if theirs else []
    minutes = chat_minutes([u.at for u in t.prior], t.now, zone)
    said = Said(t.turn, t.now, t.text, severity, None)
    added = effects_for(inputs_for(said, earlier[0].tone if earlier else None, minutes))
    stored = c.store.mood_effects_since(c.rel, t.now - MOOD_WINDOW)
    before, after = mood_at(stored, t.now, zone), mood_at([*stored, *added], t.now, zone)
    held = held_because(severity=severity, text=t.text, in_scene=in_scene is not Frame.REAL)
    shown, why = mood_line(after, held=held), mood_reason(after, held=held)
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            f"{why} [{c.mood}]",
            t.now,
            detail={
                "mode": c.mood,
                "params": MOOD_PARAMS,
                "before": {s.value: round(v, 3) for s, v in before.strengths.items()},
                "after": {s.value: round(v, 3) for s, v in after.strengths.items()},
                "added": [[e.source.value, round(e.amount, 3)] for e in added],
                "line": shown,
            },
        )
    )
    return (shown if c.mood == "on" else None), added


_BESIDE: set[asyncio.Task[None]] = set()  # shadow look-ups still running, kept from collection


def _relevance_beside(
    c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None, card: Card
) -> None:
    """Start the relevance look-up beside the turn on an ordinary message (shadow). It logs what it
    would have kept in mind and never holds up or changes the reply."""
    if c.embedder is None or c.judge is None or heard is None or in_scene is not Frame.REAL:
        return
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    on_card = [b.id for b in (*card.usable, *card.held, *card.older)]

    async def run(embedder: Embedder, judge: Extractor) -> None:
        found = await relevance_shadow(
            c.store,
            embedder,
            judge,
            c.rel,
            model=c.embed_model,
            said=t.text,
            last_reply=replies[-1] if replies else None,
            sharing=heard[0].severity >= 1,
            on_card=on_card,
            now=t.now,
        )
        if found is None:
            return
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                c.rel,
                t.session,
                t.turn,
                TraceId(t.turn),
                DecisionKind.POLICY,
                RELEVANCE_SHADOW,
                t.now,
                detail=found.detail,
            )
        )

    task = asyncio.get_running_loop().create_task(run(c.embedder, c.judge))
    _BESIDE.add(task)
    task.add_done_callback(_BESIDE.discard)


LOOP_OFFERED = "open loop: offered as a note when they wrote"
LOOP_NOTE_EVERY = timedelta(hours=24)


def _loop_note(c: Conversation, t: _Turn, *, casual: bool) -> str | None:
    """Bring up one due open loop as a note when they write (J15): on a casual turn with no other
    nudge, at most one a day, each loop at most twice. The loop is marked asked, so it is never
    also a reach-out."""
    if not casual or c.store.decided_since(c.rel, LOOP_OFFERED, t.now - LOOP_NOTE_EVERY):
        return None
    offers = c.store.loop_events_with_reason(c.rel, LOOP_OFFERED)
    loop = pick_note(c.store.open_loops(c.rel), offers, t.now, local_zone())
    if loop is None:
        return None
    c.store.open_loop_event(loop.id, LoopState.ASKED, LOOP_OFFERED, t.now)
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            LOOP_OFFERED,
            t.now,
            detail={
                "loop_id": loop.id,
                "claim": loop.claim,
                "kind": loop.kind.value,
                "offer": offers.get(loop.id, 0) + 1,
                "note": loop_note_ref(loop),
            },
        )
    )
    return loop_note(loop)


def _casual(t: _Turn, in_scene: Frame, heard: _Heard | None) -> bool:
    """An ordinary moment: read as not serious, not in a scene, not a goodbye."""
    return (
        heard is not None
        and heard[0].severity == 0
        and in_scene is Frame.REAL
        and held_because(severity=0, text=t.text, in_scene=False) is None
    )


def _map_shadow(c: Conversation, t: _Turn, *, casual: bool, asking_name: bool) -> None:
    """Log the gap it would ask about on a casual turn, at most once a day (J48, shadow). Nothing
    reaches the talker. The name comes first, so nothing is picked while that note is offered."""
    if not casual or asking_name:
        return
    if c.store.decided_since(c.rel, WOULD_ASK, t.now - MAP_EVERY):
        return
    gap = pick_gap(c.store.user_beliefs(c.rel), c.store.belief_labels(c.rel))
    if gap is None:
        return
    c.store.append_decision(
        Decision(
            DecisionId(_id()),
            c.rel,
            t.session,
            t.turn,
            TraceId(t.turn),
            DecisionKind.POLICY,
            WOULD_ASK,
            t.now,
            detail={
                "why": gap.reason,
                "domain": gap.domain.value,
                "depth": gap.depth.value,
                "counts": {d.value: n for d, n in gap.counts.items()},
            },
        )
    )


def _ask_name(
    c: Conversation, t: _Turn, in_scene: Frame, heard: _Heard | None, beliefs: Sequence[Belief]
) -> str | None:
    """Offer to ask what to call them on a casual turn, at most once a day, until memory knows."""
    casual = _casual(t, in_scene, heard)
    note = ask_name(
        known=knows_name(beliefs),
        casual=casual,
        asked_recently=c.store.decided_since(c.rel, ASKED_NAME, t.now - ASK_NAME_EVERY),
    )
    if note is not None:
        c.store.append_decision(
            Decision(
                DecisionId(_id()),
                c.rel,
                t.session,
                t.turn,
                TraceId(t.turn),
                DecisionKind.POLICY,
                ASKED_NAME,
                t.now,
            )
        )
    return note


def _assemble(  # noqa: PLR0913
    c: Conversation,
    t: _Turn,
    in_scene: Frame,
    heard: _Heard | None,
    recalled: Recalled | None,
    *,
    held: bool = False,
    roleplay: bool = False,
) -> _Assembled:
    store, now = c.store, t.now
    view_state = store.view_state(c.rel)
    views = card_views(store.self_beliefs(c.rel), view_state)
    assertable = [b for b in store.user_beliefs(c.rel) if is_assertable(b)]
    sharing = heard is not None and heard[0].severity >= 1
    card = build_card(assertable, store.last_support(c.rel), now, views=views, show_held=sharing)
    shown = [] if card.empty else [render(card, now.astimezone().tzinfo or UTC)]
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    clock = now_line(now, theirs[-1].at if theirs else None)
    pinned = address_note(store.setting(c.rel, ADDRESS_KEY))
    notes = _notes(c, t.prior, in_scene, _length(c, t, in_scene, heard))
    listening = _listening_note(c, t, heard)
    rude = rude_note(heard[0]) if heard is not None else None
    repair = repair_note(heard[0]) if heard is not None else None
    # In a scene an empty look-up adds nothing: what they mean is most likely in the story itself,
    # in view, and "memory holds nothing" would make it deny something it can see.
    empty_in_scene = in_scene is not Frame.REAL and recalled is not None and not recalled.picked
    found = recall_note(recalled.picked) if recalled is not None and not empty_in_scene else None
    mood, mood_effects = _mood(c, t, in_scene, heard)
    hold = HOLD_NOTE.text if held else None
    name = _ask_name(c, t, in_scene, heard, assertable)
    casual = _casual(t, in_scene, heard)
    _map_shadow(c, t, casual=casual, asking_name=name is not None)
    loop = _loop_note(c, t, casual=casual and name is None and not held)
    notes += [n for n in (listening, rude, repair, found, mood, hold, name, loop) if n is not None]
    card_text = "\n".join([clock, *([pinned] if pinned else []), *shown, *notes])
    prefix = c.roleplay_prefix if roleplay and c.roleplay_prefix is not None else c.prefix
    request = build_request(prefix, to_messages(t.prior), t.text, "", card_text)
    store.save_prefix(prefix)
    _mark_start(t, in_scene, card, card_text)
    return _Assembled(request, card_text, card, views, view_state, mood_effects)


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str | Reaction | ReactAndReply:
    store, rel = c.store, c.rel
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
        said = _store_user(c, t, channel, in_scene)
        await _capture_name(c, t, said)
        _mark(t, "done: reaction only")
        log.info("turn %s | ack -> %s\n  you: %s", turn[:8], reaction.emoji, text)
        return reaction
    try:
        talker, held, read = await _route(c, t, in_scene, heard)
    except BaseException:
        _store_user(c, t, channel, Frame.REAL)
        raise
    recalled = await _recall(c, t, heard or read)
    asm = _assemble(
        c, t, in_scene, heard, recalled, held=held, roleplay=talker is c.roleplay_talker
    )
    request, card_text, card, views, view_state = (
        asm.request,
        asm.card_text,
        asm.card,
        asm.views,
        asm.view_state,
    )
    _relevance_beside(c, t, in_scene, heard, card)
    talk, framing, feeling = _start_beside(c, t, request, talker)
    try:
        reply, outcome, felt = await _await_beside(t, talk, framing, feeling)
        reply = await _checked(c, t, request, reply, heard, in_scene, talker, held=held)
    except BaseException:
        await _stop(talk, framing, feeling)
        _store_user(c, t, channel, Frame.REAL)
        raise
    user_frame = frame_resolve(outcome[0] if outcome else None, fallback=in_scene)
    said = _store_user(c, t, channel, user_frame)
    if asm.mood:
        store.add_mood_effects(rel, asm.mood)
    if framing is not None:
        _log_frame(c, t, outcome, user_frame)
    store.record_turn(
        TurnRecord(
            turn,
            rel,
            session,
            request.prefix.sha256,
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
    await _capture_name(c, t, said)
    return _with_reaction(c, t, felt, sent)
