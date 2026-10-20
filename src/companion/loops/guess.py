"""Ask whether they invite a guess and look up what they may mean (J16); a failure, no note."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.extractor import Extractor, from_fallback
from companion.core.guess import JUDGE, MAX_OFFERED, SCHEMA, judge_prompt, offerable, parse
from companion.core.spend import purpose
from companion.core.types import Belief, Utterance
from companion.loops.recall import look_up

TIMEOUT_SECONDS = 3.0
log = logging.getLogger("companion.guess")


@dataclass(frozen=True, slots=True)
class Invited:
    about: str
    offered: tuple[Belief, ...]


async def invited_guess(
    extractor: Extractor, prior: Sequence[Utterance], said: str, beliefs: Sequence[Belief]
) -> Invited | None:
    try:
        with purpose("guess"):
            result = await asyncio.wait_for(
                extractor.extract(JUDGE.text, judge_prompt(prior, said), SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("guess judge failed or timed out; no note: %r", err)
        return None
    about = None if from_fallback(result.model) else parse(result.data)
    if about is None:
        return None
    found = await look_up(extractor, offerable(beliefs), about)
    picked = found.picked[:MAX_OFFERED] if found is not None else ()
    return Invited(about, tuple(picked))
