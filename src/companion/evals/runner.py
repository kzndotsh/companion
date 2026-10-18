"""Replay recorded turns against variants, score every reply, and stop at a spend cap.

A variant is a persona (a prefix) and optionally a model, with the state card kept or stripped. The
recorded history and your message are reused exactly, so the only thing that changes between
variants is the thing under test.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from companion.core.extractor import Extractor
from companion.core.habits import echo_note
from companion.core.length import length_target
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.talker import Reply, Talker
from companion.evals.checks import Verdict, run_deterministic
from companion.evals.fixtures import EmpathyCheck, Fixture, JudgeCheck
from companion.evals.judge import grade, grade_empathy

CONCURRENCY = 4
FREE_SPACING_SECONDS = 3.1
RETRIES = 3
RETRY_WAIT_SECONDS = 2.0
_CARD_BLOCK = re.compile(r"^\[(?:What you remember|Also known).*?\]\n?", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class Variant:
    label: str
    prefix: Prefix
    keep_card: bool = True
    model: str | None = None
    history: int | None = None  # keep only this many of the last messages
    effort: str | None = None  # reasoning effort; None keeps it off, as in the bot
    length: bool = False  # add the length note the bot adds to a short statement
    listen: bool = False  # add the listening note a fixture's labels would produce
    echo: bool = False  # add the note against copying their emoji, when they used one


@dataclass(frozen=True, slots=True)
class Sample:
    reply: str
    verdicts: tuple[Verdict, ...]
    latency_ms: int
    cost_usd: float

    @property
    def outcome(self) -> Verdict:
        if "fail" in self.verdicts:
            return "fail"
        return "unclear" if "unclear" in self.verdicts else "pass"


@dataclass(slots=True)
class Cell:
    """All samples for one fixture under one variant."""

    samples: list[Sample] = field(default_factory=list[Sample])
    skipped: int = 0

    def count(self, outcome: Verdict) -> int:
        return sum(s.outcome == outcome for s in self.samples)


@dataclass(slots=True)
class Results:
    cells: dict[tuple[str, str], Cell]
    spent: float = 0.0
    stopped_by_cap: bool = False


def strip_card(content: str) -> str:
    """The user message without the memory blocks, keeping the clock line and what they typed."""
    return _CARD_BLOCK.sub("", content)


def request_for(
    base: TalkerRequest, variant: Variant, listening: str | None = None
) -> TalkerRequest:
    messages = list(base.messages)
    if variant.history is not None:
        messages = messages[-variant.history :]
    if not variant.keep_card:
        last = messages[-1]
        messages[-1] = Message(last.role, strip_card(last.content))
    card = base.card if variant.keep_card else ""
    if variant.length and (size := length_target(messages[-1].content)):
        note = size.note
        card = f"{card}\n{note}" if card else note
    if variant.echo and (echo := echo_note(messages[-1].content)):
        card = f"{card}\n{echo}" if card else echo
    if variant.listen and listening:
        card = f"{card}\n{listening}" if card else listening
    return TalkerRequest(prefix=variant.prefix, messages=tuple(messages), card=card)


@dataclass(frozen=True, slots=True)
class Plan:
    fixtures: Sequence[Fixture]
    requests: Mapping[str, TalkerRequest]
    variants: Sequence[Variant]
    samples: int
    cap_usd: float
    listening: Mapping[str, str] = field(default_factory=dict[str, str])


@dataclass(frozen=True, slots=True)
class Models:
    talker_for: Callable[[str | None, str | None], Talker]
    judge: Extractor


async def _reply_with_retry(talker: Talker, req: TalkerRequest) -> Reply | None:
    """A provider that rate-limits or errors costs one sample, not the whole run."""
    for attempt in range(RETRIES):
        try:
            return await talker.reply(req)
        except Exception:
            await asyncio.sleep(RETRY_WAIT_SECONDS * (attempt + 1))
    return None


def _free(model: str | None) -> bool:
    """Free endpoints are rate-limited: the Kiro gateway and OpenRouter's `:free` models."""
    return model is not None and (model.startswith("kiro/") or model.endswith(":free"))


async def run_eval(plan: Plan, models: Models) -> Results:
    results = Results(cells={(f.id, v.label): Cell() for f in plan.fixtures for v in plan.variants})
    free = any(_free(v.model) for v in plan.variants)
    gate = asyncio.Semaphore(
        1 if free else CONCURRENCY
    )  # the free gateway takes one call at a time

    async def one(f: Fixture, v: Variant) -> None:
        cell = results.cells[(f.id, v.label)]
        async with gate:
            if results.spent >= plan.cap_usd:
                results.stopped_by_cap = True
                cell.skipped += 1
                return
            req = request_for(plan.requests[f.id], v, plan.listening.get(f.id))
            reply = await _reply_with_retry(models.talker_for(v.model, v.effort), req)
            if (v.model or "").endswith(":free"):
                await asyncio.sleep(FREE_SPACING_SECONDS)  # OpenRouter allows 20 a minute
            if reply is None:
                cell.skipped += 1
                return
            results.spent += reply.cost_usd
            verdicts: list[Verdict] = []
            cost = reply.cost_usd
            for check in f.checks:
                if isinstance(check, JudgeCheck):
                    graded = await grade(models.judge, req.messages, reply.text, check.criterion)
                    results.spent += graded.cost_usd
                    cost += graded.cost_usd
                    verdicts.append(graded.verdict)
                elif isinstance(check, EmpathyCheck):
                    graded = await grade_empathy(models.judge, req.messages, reply.text)
                    results.spent += graded.cost_usd
                    cost += graded.cost_usd
                    verdicts.append(graded.verdict)
                else:
                    verdicts.append(run_deterministic(check, reply.text))
            cell.samples.append(Sample(reply.text, tuple(verdicts), reply.latency_ms, cost))

    await asyncio.gather(
        *(one(f, v) for f in plan.fixtures for v in plan.variants for _ in range(plan.samples))
    )
    return results
