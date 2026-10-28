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

from companion.core.extractor import Extraction, StructuredModel, from_fallback, judging
from companion.core.spend import purpose
from companion.core.types import Json
from companion.lib.prompts import Prompt

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
    attempts: int = 1  # tries when a call fails or runs out of time; an unreadable answer is final
    # With attempts left, the next try starts once a try has gone this long without answering,
    # and the slow one keeps running: the first answer wins. None: the next try waits for the
    # last to fail or time out.
    hedge: float | None = None


@dataclass(frozen=True, slots=True)
class Read[T]:
    value: T
    model: str
    cost_usd: float
    ref: str  # the prompt's name@version, for the decision it feeds


async def ask[T](extractor: StructuredModel, judge: Judge[T], user: str) -> Read[T] | None:
    """Ask the judge once. None when the call failed, ran past its time, came from the fallback
    model where that is not trusted, or could not be parsed, each logged with what it means."""
    got = await _first_answer(extractor, judge, user)
    if got is None:
        log.warning("%s judge could not be read; %s", judge.name, judge.unread)
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


async def _first_answer[T](
    extractor: StructuredModel, judge: Judge[T], user: str
) -> Extraction | None:
    """The first try to answer within its time. A try starts at the beginning, when one fails, and,
    with a hedge, when the running ones have gone that long without answering; whatever is still
    running when one answers is cancelled."""
    running: dict[asyncio.Task[Extraction], int] = {}  # each try and its number

    async def one() -> Extraction:
        with purpose(judge.name), judging(judge.name):
            call = extractor.extract(judge.prompt.text, user, judge.schema)
            return await asyncio.wait_for(call, judge.timeout)

    def start() -> None:
        task = asyncio.ensure_future(one())
        task.add_done_callback(
            lambda t: t.cancelled() or t.exception()
        )  # a late failure stays quiet
        running[task] = started[0] = started[0] + 1

    started = [0]
    start()
    try:
        while running:
            hedge = judge.hedge if started[0] < judge.attempts else None
            done, _ = await asyncio.wait(
                running, timeout=hedge, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                attempt = running.pop(task)
                if (err := task.exception()) is None:
                    return task.result()
                log.warning("%s judge failed or timed out (try %d): %r", judge.name, attempt, err)
            if started[0] < judge.attempts and (not done or not running):
                start()
        return None
    finally:
        for task in running:
            task.cancel()
