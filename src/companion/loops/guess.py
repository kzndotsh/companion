"""Ask whether they invite a guess and look up what they may mean (J16); a failure, no note."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.extractor import Extractor
from companion.core.guess import JUDGE, MAX_OFFERED, SCHEMA, judge_prompt, offerable, parse
from companion.core.types import Belief, Utterance
from companion.loops.ask import Judge, ask
from companion.loops.recall import look_up

TIMEOUT_SECONDS = 3.0
INVITE = Judge(
    "guess", JUDGE, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note", trust_fallback=False
)


@dataclass(frozen=True, slots=True)
class Invited:
    about: str
    offered: tuple[Belief, ...]


async def invited_guess(
    extractor: Extractor, prior: Sequence[Utterance], said: str, beliefs: Sequence[Belief]
) -> Invited | None:
    got = await ask(extractor, INVITE, judge_prompt(prior, said))
    if got is None:
        return None
    about = got.value
    found = await look_up(extractor, offerable(beliefs), about)
    picked = found.picked[:MAX_OFFERED] if found is not None else ()
    return Invited(about, tuple(picked))
