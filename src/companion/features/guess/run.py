"""Ask whether they invite a guess and look up what they may mean (J16); a failure, no note."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.types import Belief, Frame, Utterance
from companion.features.guess.logic import INVITED as GUESS_INVITED
from companion.features.guess.logic import (
    JUDGE,
    MAX_OFFERED,
    SCHEMA,
    judge_prompt,
    offerable,
    parse,
)
from companion.features.guess.logic import NOTE as GUESS_NOTE
from companion.features.guess.logic import likely as guess_likely
from companion.features.guess.logic import note as guess_note
from companion.kit.ask import Judge, ask
from companion.kit.current import Heard, Turn, decide, is_casual, mark
from companion.kit.features import Feature, Offer, Offered
from companion.kit.recall import look_up

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

TIMEOUT_SECONDS = 3.0
INVITE = Judge(
    "guess", JUDGE, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note", trust_fallback=False
)


@dataclass(frozen=True, slots=True)
class Invited:
    about: str
    offered: tuple[Belief, ...]


async def invited_guess(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str, beliefs: Sequence[Belief]
) -> Invited | None:
    got = await ask(extractor, INVITE, judge_prompt(prior, said))
    if got is None:
        return None
    about = got.value
    found = await look_up(extractor, offerable(beliefs), about)
    picked = found.picked[:MAX_OFFERED] if found is not None else ()
    return Invited(about, tuple(picked))


async def guess_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> Invited | None:
    """When their short question invites a guess about them (J16), what memory holds that may fit.
    Casual turns only, and never when they asked it to remember something (recall answers that);
    logged with what was offered, so guesses can later be scored by kind."""
    if heard is not None and heard[0].recall:
        return None
    if c.judge is None or not is_casual(t, in_scene, heard) or not guess_likely(t.text):
        return None
    mark(t, "guess judge")
    found = await invited_guess(c.judge, t.prior, t.text, c.store.user_beliefs(c.rel))
    if found is not None:
        decide(
            c,
            t,
            GUESS_INVITED,
            {
                "about": found.about,
                "offered": [b.claim for b in found.offered],
                "note": GUESS_NOTE.ref,
            },
        )
    return found


def guess_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """One note to make a single playful guess, as a question, from what memory may hold."""
    del m, so_far
    g = found if isinstance(found, Invited) else None
    note = guess_note(g.about, g.offered) if g is not None else None
    return Offer((note,) if note else (), asks=True)


GUESS = Feature("guess", look=guess_for_turn, note=guess_offer)
