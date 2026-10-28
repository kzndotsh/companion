"""Ask whether a small topic has run its course, with a time limit. A failure means no note."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.clock import local_zone
from companion.core.extractor import StructuredModel
from companion.core.types import Frame, Speaker, Utterance
from companion.features.topics.logic import EVERY_TURNS as TOPIC_EVERY
from companion.features.topics.logic import JUDGE, SCHEMA, asks, judge_prompt, parse, topic_note
from companion.features.topics.logic import NOTE as TOPIC_NOTE
from companion.features.topics.logic import SPENT as TOPIC_SPENT
from companion.features.topics.logic import likely as topic_likely
from companion.loops.ask import Judge, ask
from companion.loops.current import Heard, Turn, decide, is_casual, mark
from companion.loops.features import Feature, Offer, Offered, has_room

if TYPE_CHECKING:
    from companion.loops.features import Moment
    from companion.loops.runtime import Runtime

TIMEOUT_SECONDS = 3.0
SPENT = Judge(
    "topics", JUDGE, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note", trust_fallback=False
)


async def judge_spent(extractor: StructuredModel, prior: Sequence[Utterance], said: str) -> bool:
    got = await ask(extractor, SPENT, judge_prompt(prior, said))
    return got is not None and got.value


async def spent_for_turn(c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None) -> bool:
    """Whether a small topic has run its course: asked of its own judge only on a likely moment on
    a casual turn, so the listening judge, which carries the age floor, stays as it was."""
    if c.judge is None or not is_casual(t, in_scene, heard) or not topic_likely(t.prior, t.text):
        return False
    mark(t, "topic judge")
    return await judge_spent(c.judge, t.prior, t.text)


def _move_on(m: Moment, found: object, *, casual: bool, loop_offered: bool) -> Offer:
    """When a small topic has run its course, one line to move on, at most once in EVERY_TURNS of
    their messages. Recorded with the move it named once the reply is stored."""
    c, t = m.c, m.t
    if found is not True or "?" in t.text:
        return Offer()  # a question of theirs is answered, never moved past
    theirs = [u.turn_id for u in t.prior if u.speaker is Speaker.USER][-(TOPIC_EVERY - 1) :]
    recent = any(
        d.has_key(TOPIC_SPENT) for turn in theirs for d in c.store.decisions_for_turn(c.rel, turn)
    )
    found = topic_note(
        spent=True,
        casual=casual,
        moved_recently=recent,
        local_hour=t.now.astimezone(local_zone()).hour,
        loop_offered=loop_offered,
    )
    if found is None:
        return Offer()
    note, move = found
    return Offer(
        (note,),
        (lambda: decide(c, t, TOPIC_SPENT, {"move": move.ref, "note": TOPIC_NOTE.ref}),),
        asks=asks(move),
    )


def topic_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """On a quiet turn, knowing whether a plan of theirs was just brought up: the picker sends a
    plan in the system block and a day after the history (`turn/mention.py`)."""
    return _move_on(
        m, found, casual=has_room(m, so_far), loop_offered=bool(so_far["mention"].lines)
    )


TOPICS = Feature("topic", look=spent_for_turn, note=topic_offer)
