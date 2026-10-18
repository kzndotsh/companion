"""Reading what they said for loops worth asking about, and the one tick that decides to ask.

Extraction runs inside the slow loop's batch, after the beliefs, and costs one small call. The tick
runs on a timer, reads the store, asks the pure gate in `core/initiative.py`, and in shadow mode
only records what it would have sent. Nothing here sends a message.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, tzinfo

from companion.core.beliefs.extract import build_user_prompt
from companion.core.clock import local_midnight
from companion.core.extractor import Extractor
from companion.core.frames import scene_frame
from companion.core.initiative import Caps, Situation, Verdict, evaluate
from companion.core.openloops import (
    PROMPT,
    SCHEMA,
    SYSTEM,
    LoopState,
    Making,
    OpenLoop,
    normalise,
    parse,
    to_loop,
)
from companion.core.spend import purpose
from companion.core.types import (
    Decision,
    DecisionId,
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.prompts import get
from companion.store.sqlite.open_loops import ReachOut
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.initiative")
MAX_DRAFT_WORDS = 18
SESSION = SessionId("initiative")
Draft = Callable[[OpenLoop], Awaitable[str]]
Log = Callable[[str, dict[str, Json]], None]


@dataclass(frozen=True, slots=True)
class LoopCounts:
    candidates: int = 0
    stored: int = 0
    rejected: int = 0
    cost_usd: float = 0.0


def _id() -> str:
    return uuid.uuid4().hex


async def extract_open_loops(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    window: Mapping[str, Utterance],
    targets: set[UtteranceId],
    when: tuple[datetime, tzinfo],
    note: Log,
) -> LoopCounts:
    """Record the open loops in the targeted messages. A failure here never stops the batch."""
    now, tz = when
    try:
        with purpose("loops"):
            result = await extractor.extract(
                SYSTEM, build_user_prompt(window, targets, {}, tz), SCHEMA
            )
    except Exception:
        log.warning("open-loop extraction failed; skipping this batch", exc_info=True)
        return LoopCounts()
    raw = parse(result.data)
    if raw is None:
        note("open loops: the answer was malformed and was ignored", {"model": result.model})
        return LoopCounts(cost_usd=result.cost_usd)
    known = {normalise(lp.claim) for lp in store.open_loops(rel)}
    made = Making(rel, now, tz, _id)
    stored = rejected = 0
    for item in raw:
        outcome = to_loop(item, window, made)
        if isinstance(outcome, str):
            rejected += 1
            note(f"open loop rejected: {outcome}", {"claim": item.claim, "quote": item.quote})
        elif normalise(outcome.claim) in known:
            rejected += 1
            note("open loop rejected: already recorded", {"claim": outcome.claim})
        else:
            store.add_open_loop(outcome)
            known.add(normalise(outcome.claim))
            stored += 1
            note(
                "open loop recorded from their own words",
                {
                    "loop_id": outcome.id,
                    "claim": outcome.claim,
                    "quote": outcome.quote,
                    "follow_up_at": outcome.follow_up_at.isoformat(),
                    "model": result.model,
                    "prompt": PROMPT.ref,
                },
            )
    log.debug("open loops: %d proposed, %d stored, %d rejected", len(raw), stored, rejected)
    return LoopCounts(len(raw), stored, rejected, result.cost_usd)


@dataclass(slots=True)
class Ticker:
    """Remembers which holds it has already recorded, so a hold that lasts hours is one decision
    and not ninety-six."""

    seen: set[tuple[str, str]] = field(default_factory=set[tuple[str, str]])


def _decision(
    rel: RelationshipId, kind: DecisionKind, reason: str, now: datetime, detail: dict[str, Json]
) -> Decision:
    trace = _id()
    return Decision(
        DecisionId(_id()),
        rel,
        SESSION,
        TurnId(trace),
        TraceId(trace),
        kind,
        reason,
        now,
        detail=detail,
    )


def _situation(store: Store, rel: RelationshipId, now: datetime, tz: tzinfo) -> Situation:
    recent = store.history_before(rel, now, 8)
    sent = store.reach_outs(rel)
    today = [r for r in sent if r.at >= local_midnight(now)]
    return Situation(
        now=now,
        tz=tz,
        last_message_at=recent[-1].at if recent else None,
        in_scene=scene_frame(recent) is not Frame.REAL,
        sent_today=len(today),
        last_reach_out_at=max((r.at for r in sent), default=None),
    )


async def tick(  # noqa: PLR0913, PLR0917
    store: Store,
    rel: RelationshipId,
    now: datetime,
    tz: tzinfo,
    draft: Draft | None,
    ticker: Ticker,
    caps: Caps = Caps(),  # noqa: B008
) -> Verdict:
    """One look at the open loops. In shadow mode a verdict to send is recorded with a drafted
    message and the loop is marked asked, but nothing is sent."""
    verdict = evaluate(store.open_loops(rel), _situation(store, rel, now, tz), caps)
    for lp in verdict.expired:
        store.open_loop_event(lp.id, LoopState.EXPIRED, "past its follow-up horizon", now)
        store.append_decision(
            _decision(
                rel, DecisionKind.POLICY, f"open loop expired: {lp.claim}", now, {"loop_id": lp.id}
            )
        )
    if verdict.loop is None:
        log.debug("initiative: %s", verdict.reason)
        return verdict
    detail: dict[str, Json] = {"loop_id": verdict.loop.id, "claim": verdict.loop.claim}
    if not verdict.send:
        key = (verdict.loop.id, verdict.reason)
        if key not in ticker.seen:
            ticker.seen.add(key)
            reason = f"held, would otherwise reach out about {verdict.loop.claim}: {verdict.reason}"
            store.append_decision(_decision(rel, DecisionKind.DO_NOTHING, reason, now, detail))
            log.info("initiative held: %s (%s)", verdict.loop.claim, verdict.reason)
        return verdict
    text = await draft(verdict.loop) if draft is not None else ""
    store.add_reach_out(ReachOut(_id(), rel, verdict.loop.id, "shadow", text, verdict.reason, now))
    store.open_loop_event(verdict.loop.id, LoopState.ASKED, "shadow reach-out, not sent", now)
    detail["draft"] = text
    store.append_decision(
        _decision(rel, DecisionKind.INITIATE, f"shadow, would send: {verdict.reason}", now, detail)
    )
    log.info("initiative shadow: would send %r about %s", text, verdict.loop.claim)
    return verdict


DRAFT_PROMPT = get("system/openloops-draft")
DRAFT_SYSTEM = DRAFT_PROMPT.text
DRAFT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}


def drafter(extractor: Extractor) -> Draft:
    """A function that drafts the check-in for a loop. Any failure gives an empty draft."""

    async def draft(loop: OpenLoop) -> str:
        prompt = f"They said: {loop.quote!r}\nThe thing: {loop.claim}"
        try:
            with purpose("initiative"):
                result = await extractor.extract(DRAFT_SYSTEM, prompt, DRAFT_SCHEMA)
        except Exception:
            log.warning("could not draft the check-in", exc_info=True)
            return ""
        message = result.data.get("message") if isinstance(result.data, dict) else None
        return short_draft(message) if isinstance(message, str) else ""

    return draft


def short_draft(message: str) -> str:
    """The draft if it is short, its first sentence if that is a short question, else none."""
    text = " ".join(message.split())
    if len(text.split()) <= MAX_DRAFT_WORDS:
        return text
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    short = len(first.split()) <= MAX_DRAFT_WORDS and first.endswith("?")
    return first if short else ""
