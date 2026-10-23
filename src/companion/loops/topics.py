"""Ask whether a small topic has run its course, with a time limit. A failure means no note."""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core.clock import local_zone
from companion.core.topics import EVERY_TURNS as TOPIC_EVERY
from companion.core.topics import NOTE as TOPIC_NOTE
from companion.core.topics import SPENT as TOPIC_SPENT
from companion.core.topics import likely as topic_likely
from companion.core.topics import topic_note
from companion.core.types import Frame, Speaker
from companion.loops.features import Feature, Offer, Offered, quiet
from companion.loops.turn import Heard, Turn, decide, is_casual, mark

if TYPE_CHECKING:
    from companion.loops.fast import Conversation
    from companion.loops.notes import Moment

from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.topics import JUDGE, SCHEMA, judge_prompt, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 3.0
SPENT = Judge(
    "topics", JUDGE, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note", trust_fallback=False
)


async def judge_spent(extractor: Extractor, prior: Sequence[Utterance], said: str) -> bool:
    got = await ask(extractor, SPENT, judge_prompt(prior, said))
    return got is not None and got.value


async def spent_for_turn(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> bool:
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
        (note,), (lambda: decide(c, t, TOPIC_SPENT, {"move": move.ref, "note": TOPIC_NOTE.ref}),)
    )


def topic_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """On a quiet turn, knowing whether a plan of theirs was just offered as a note."""
    return _move_on(m, found, casual=quiet(m, so_far), loop_offered=bool(so_far["loop"].lines))


TOPICS = Feature("topic", look=spent_for_turn, note=topic_offer)
