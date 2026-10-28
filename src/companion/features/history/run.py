"""Its own history (ADR 0025), step 1 in shadow. After a memory pass: read its own messages past
the history bookmark for stories about its own past, then check each waiting story against the
character sheet and the canon. Beside a turn: log the canon stories nearest their message, showing
nothing. A failed or unreadable read leaves the bookmark or the story where it was, for the next
pass."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.beliefs.extract import build_user_prompt, index_window
from companion.core.clock import local_zone
from companion.core.extractor import StructuredModel
from companion.core.history import HISTORY_LIMIT
from companion.core.spend import purpose
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    Speaker,
    TraceId,
    Utterance,
    UtteranceId,
)
from companion.core.vectors import Embedder
from companion.features.history.logic import (
    CANON,
    CANON_SCHEMA,
    CAPTURE,
    CAPTURE_SCHEMA,
    Recorded,
    Standing,
    Story,
    canon_prompt,
    nearest,
    parse_canon,
    parse_capture,
    rule,
    to_story,
)
from companion.features.history.store import By
from companion.loops.current import Heard, Turn, decide, is_casual
from companion.loops.features import Feature
from companion.loops.reads import read_times
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

if TYPE_CHECKING:
    from companion.core.card import Card
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.history")

BATCH = 40  # its messages read per call, as the memory pass reads them
CONTEXT = 4  # messages before a batch shown for context
BATCHES = 3  # batches read per pass, so a long backlog is read over several passes
CHECKS = 10  # waiting stories checked per pass
LOOK_SECONDS = 2.0

CAPTURED = "history: a story of its own past recorded"
DROPPED = "history: a story dropped"
RULED = "history: the canon check ruled"
NEAREST = "history: its canon stories nearest their message (shadow)"


@dataclass(frozen=True, slots=True)
class HistoryRead:
    captured: int = 0
    ruled: int = 0
    cost_usd: float = 0.0


def _recorder(store: Store, u: Utterance, now: datetime) -> Recorder:
    return Recorder(
        store, u.relationship_id, u.session_id, u.turn_id, TraceId(uuid.uuid4().hex), now
    )


async def _capture(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
) -> tuple[int, float] | None:
    """Read one batch of messages past the bookmark: the stories kept and the cost, or None when
    nothing is left or the read failed (the bookmark stays, so it is read again)."""
    stories = store.stories()
    batch = store.utterances_after(rel, stories.cursor(rel), BATCH)
    if not batch:
        return None
    upto = (batch[-1].at, batch[-1].id)
    own = {u.id for u in batch if u.speaker is Speaker.COMPANION}
    if not own:
        stories.read_upto(rel, upto, now)
        return 0, 0.0
    window = index_window([*store.history_before(rel, batch[0].at, CONTEXT), *batch])
    try:
        with purpose("history"):
            got = await extractor.extract(
                CAPTURE.text, build_user_prompt(window, own, {}, local_zone()), CAPTURE_SCHEMA
            )
    except Exception as err:
        log.warning("history capture failed; the batch is read again next pass: %r", err)
        return None
    proposed = parse_capture(got.data)
    if proposed is None:
        log.warning("history capture answer was unreadable; the batch is read again next pass")
        return None
    known = {(r.story.utterance_id, r.story.quote.lower()) for r in stories.recorded(rel)}
    kept = 0
    for p in proposed:
        made = to_story(p, window, uuid.uuid4().hex)
        source = window.get(p.message.strip("[] "), batch[-1])
        if isinstance(made, str):
            detail: dict[str, Json] = {"claim": p.claim, "quote": p.quote, "place": p.place}
            _recorder(store, source, now).decide(DROPPED, detail, reason=f"{DROPPED}: {made}")
            continue
        if (made.utterance_id, made.quote.lower()) in known:
            continue
        stories.add(made, By(got.model, CAPTURE.ref, now))
        known.add((made.utterance_id, made.quote.lower()))
        kept += 1
        _recorder(store, source, now).decide(
            CAPTURED,
            {
                "story_id": made.id,
                "claim": made.claim,
                "quote": made.quote,
                "frame": made.frame.value,
                "prompt": CAPTURE.ref,
            },
        )
    stories.read_upto(rel, upto, now)
    return kept, got.cost_usd


async def _check(
    store: Store, extractor: StructuredModel, waiting: Story, sheet: str, now: datetime
) -> tuple[bool, float]:
    """Read one waiting story against the sheet and the canon three times and record its standing.
    False when a read failed: nothing is recorded and it waits for the next pass."""
    stories = store.stories()
    canon = [
        r.story for r in stories.recorded(waiting.relationship_id) if r.standing is Standing.CANON
    ]
    text, refs = canon_prompt(sheet, canon, waiting)
    got = await read_times(
        extractor,
        CANON.text,
        text,
        CANON_SCHEMA,
        lambda data: parse_canon(data, refs),
        spend="history",
    )
    ruling = rule(got.values, {s.id: s.claim for s in canon})
    if ruling is None:
        log.warning("history canon check: a read failed; story %s waits", waiting.id[:8])
        return False, got.cost_usd
    stories.rule(waiting.id, ruling, By(got.model, CANON.ref, now))
    source = store.get_utterance(waiting.utterance_id)
    if source is not None:
        _recorder(store, source, now).decide(
            RULED,
            {
                "story_id": waiting.id,
                "claim": waiting.claim,
                "standing": ruling.standing.value,
                "verdict": ruling.verdict.value if ruling.verdict else None,
                "of": ruling.of,
                "prompt": CANON.ref,
            },
            reason=f"history: {ruling.standing.value}: {ruling.reason}",
        )
    return True, got.cost_usd


async def read_history(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime, *, sheet: str
) -> HistoryRead:
    """Capture new stories from its own messages, then check the waiting ones, oldest first, so a
    later story is read against the earlier ones' canon."""
    captured, cost = 0, 0.0
    for _ in range(BATCHES):
        got = await _capture(store, extractor, rel, now)
        if got is None:
            break
        captured, cost = captured + got[0], cost + got[1]
    ruled = 0
    for _ in range(CHECKS):
        waiting = next((r.story for r in store.stories().recorded(rel) if r.standing is None), None)
        if waiting is None:
            break
        done, spent = await _check(store, extractor, waiting, sheet, now)
        cost += spent
        if not done:
            break
        ruled += 1
    log.debug("history: %d stories captured, %d ruled, $%.4f", captured, ruled, cost)
    return HistoryRead(captured, ruled, cost)


type Step = Callable[[Store, StructuredModel, RelationshipId, datetime], Awaitable[HistoryRead]]


def pass_step(mode: str, sheet: str) -> Step | None:
    """The step the memory pass runs for `COMPANION_HISTORY`, or None when it is off."""
    if mode == "off":
        return None

    async def step(
        store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
    ) -> HistoryRead:
        return await read_history(store, extractor, rel, now, sheet=sheet)

    return step


async def nearest_stories(
    store: Store, embed: tuple[Embedder, str], rel: RelationshipId, said: str, now: datetime
) -> list[tuple[Recorded, float]] | None:
    """Its canon stories nearest their message, embedding any with no vector yet in the same call.
    None when the call failed or was slow."""
    embedder, model = embed
    stories = store.stories()
    canon = [r for r in stories.recorded(rel) if r.standing is Standing.CANON]
    if not canon:
        return []
    have = stories.vectors(rel, model)
    missing = [r.story for r in canon if r.story.id not in have]
    try:
        with purpose("history"):
            got = await asyncio.wait_for(
                embedder.embed([said, *(s.claim for s in missing)]), LOOK_SECONDS
            )
    except Exception as err:
        log.warning("history look-up failed or was slow: %r", err)
        return None
    if missing:
        fresh = dict(zip((s.id for s in missing), got.vectors[1:], strict=True))
        stories.add_vectors(fresh, model, now)
        have = {**have, **fresh}
    return nearest(got.vectors[0], canon, have)


async def stories_beside(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, card: Card
) -> None:
    """Log the canon stories it would show on an ordinary turn, and whether each was told already
    and is still in the messages the talker reads. Shows nothing (step 1)."""
    del card
    if c.history == "off" or c.embedder is None or not is_casual(t, in_scene, heard):
        return
    found = await nearest_stories(c.store, (c.embedder, c.embed_model), c.rel, t.text, t.now)
    if not found:
        return
    in_view: set[UtteranceId] = {u.id for u in c.store.history_before(c.rel, t.now, HISTORY_LIMIT)}
    shown = [r for r, _ in found]
    fresh = sum(not in_view.intersection(r.told) for r in shown)
    decide(
        c,
        t,
        NEAREST,
        {
            "stories": [r.story.id for r in shown],
            "scores": [round(s, 3) for _, s in found],
            "claims": [r.story.claim for r in shown],
            "told": [len(r.told) for r in shown],
            "last_told": [r.last_told.isoformat() for r in shown],
            "in_view": [bool(in_view.intersection(r.told)) for r in shown],
        },
        reason=f"{NEAREST}: {len(shown)} near, {fresh} told before and out of view",
    )


HISTORY = Feature("history", shadow=stories_beside)
