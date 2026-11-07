"""Reading the companion's recent replies for what they keep repeating, in the background after a
reply, and the note that tells the next replies. Live; a failed read means no note."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.turn.context import Scored
from companion.core.types import Json, Utterance
from companion.features.diction.tics.logic import (
    FRESH_FOR,
    PROMPT,
    SCHEMA,
    build_prompt,
    note_for,
    parse,
    replies_to_read,
    tic_note,
)
from companion.kit.ask import Judge, ask
from companion.kit.current import decide
from companion.kit.features import Feature, Moment, NoteName, Offer, Offered

if TYPE_CHECKING:
    pass

TIMEOUT_SECONDS = 6.0
TICS_JUDGE = Judge("tics", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note")


async def find_tics(extractor: StructuredModel, replies: Sequence[str]) -> Scored[list[str]] | None:
    """The habits, the model id and the prompt, or None if they could not be found in time."""
    prompt = build_prompt(replies)
    got = await ask(extractor, TICS_JUDGE, prompt)
    return None if got is None else Scored(got.value, got.model, prompt)


async def check_tics(m: Moment, said: Utterance, sent: str | None) -> None:
    """After the reply is out, read the last few replies in the background for habits."""
    del said
    c, t = m.c, m.t
    if not sent:
        return
    replies = replies_to_read(t.prior, sent)
    if not replies:
        return

    async def look() -> list[str] | None:
        found = await find_tics(m.judge, replies)
        if found is None:
            return None
        habits = found.read
        detail = found.detail(PROMPT.ref, habits=list[Json](habits))
        decide(
            c,
            t,
            "habit check",
            detail,
            reason=f"habit check: {len(habits)} habits found in the last {len(replies)} replies",
        )
        return habits

    await c.tics.run(look())


def tics_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """Its own tics: the openings and moves its recent replies repeat, by code, and what the
    last background check found while it is fresh."""
    del found, so_far
    lines = [tic_note(m.t.prior, words=m.casual), note_for(m.c.tics.fresh(FRESH_FOR))]
    return Offer(tuple(line for line in lines if line is not None))


# What its replies keep repeating, read after each reply and shown to the next ones.
TICS = Feature(NoteName.TICS, note=tics_offer, after_turn=check_tics, needs_judge=True)
