"""One way to ask a judge (architecture audit, 2026-10-23).

A judge is declared once, as a `Judge`: its prompt, its schema, how its answer is parsed, how long
it may take, whether a fallback model's reading counts, and what a failure means for the feature.
`ask` runs it: the cost tag, the time limit, the log line and the parse live here and nowhere else.
It returns a `Read` with the value, the model, the cost and the prompt's `name@version`, or None
when nothing usable came back; the caller says what None means in one line.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from companion.core.extractor import Extractor, from_fallback
from companion.core.spend import purpose
from companion.core.types import Json
from companion.prompts import Prompt

log = logging.getLogger("companion.judges")


@dataclass(frozen=True, slots=True)
class Judge[T]:
    name: str  # the log's name for it, and its spend purpose
    prompt: Prompt  # the system prompt, versioned
    schema: dict[str, Json]
    parse: Callable[[Json], T | None]  # None: the answer could not be read
    timeout: float  # seconds
    unread: str  # what a failed or unusable read means, for the log ("no note")
    trust_fallback: bool = True  # False: a fallback model's answer counts as unread (ADR 0017)


@dataclass(frozen=True, slots=True)
class Read[T]:
    value: T
    model: str
    cost_usd: float
    ref: str  # the prompt's name@version, for the decision it feeds


async def ask[T](extractor: Extractor, judge: Judge[T], user: str) -> Read[T] | None:
    """Ask the judge once. None when the call failed, ran past its time, came from the fallback
    model where that is not trusted, or could not be parsed, each logged with what it means."""
    try:
        with purpose(judge.name):
            got = await asyncio.wait_for(
                extractor.extract(judge.prompt.text, user, judge.schema), judge.timeout
            )
    except Exception as err:
        log.warning("%s judge failed or timed out; %s: %r", judge.name, judge.unread, err)
        return None
    if not judge.trust_fallback and from_fallback(got.model):
        log.info(
            "%s judge answered by the fallback model, not trusted; %s", judge.name, judge.unread
        )
        return None
    value = judge.parse(got.data)
    if value is None:
        log.warning("%s judge gave an unreadable answer; %s", judge.name, judge.unread)
        return None
    log.debug("%s judge: %r, $%.5f, %dms", judge.name, value, got.cost_usd, got.latency_ms)
    return Read(value, got.model, got.cost_usd, judge.prompt.ref)
