"""Run fixtures against variants, score every reply, and stop at a spend cap.

A variant is a persona (a prefix) and optionally a model, with the request's shape around it. Each
sample is what the person would receive: the turn's own notes and reply checks (`evals/sample.py`).
A recorded turn's history and message are reused exactly, so the only thing that changes between
variants is the thing under test.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from companion.core.extractor import Extraction, StructuredModel
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply, Talker
from companion.core.types import Json
from companion.evals.checks import Verdict, run_deterministic
from companion.evals.fixtures import EmpathyCheck, Fixture, JudgeCheck
from companion.evals.judge import grade, grade_empathy
from companion.evals.sample import Variant, draw

CONCURRENCY = 4
FREE_SPACING_SECONDS = 3.1
RETRIES = 3
RETRY_WAIT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class Sample:
    reply: str
    verdicts: tuple[Verdict, ...]
    latency_ms: int
    cost_usd: float
    redrawn: tuple[str, ...] = ()  # the checks that made the turn draw again, in order

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
    charged: float | None = None  # what OpenRouter's meter moved by, read after the run


@dataclass(frozen=True, slots=True)
class Plan:
    fixtures: Sequence[Fixture]
    requests: Mapping[str, TalkerRequest]
    variants: Sequence[Variant]
    samples: int
    cap_usd: float
    # a request rebuilt for one variant of one recorded turn (+cardN, +histN), by (fixture, label)
    rebuilt: Mapping[tuple[str, str], TalkerRequest] = field(
        default_factory=dict[tuple[str, str], TalkerRequest]
    )


@dataclass(frozen=True, slots=True)
class Models:
    talker_for: Callable[[str | None, str | None], Talker]
    judge: StructuredModel


class _Metered:
    """The variant's talker as a sample uses it: a provider that rate-limits or errors is tried
    again, and every reply's cost is added up, redraws included."""

    def __init__(self, talker: Talker) -> None:
        self.talker, self.spent = talker, 0.0

    async def reply(self, request: TalkerRequest) -> Reply:
        for attempt in range(RETRIES - 1):
            try:
                return self._count(await self.talker.reply(request))
            except Exception:
                await asyncio.sleep(RETRY_WAIT_SECONDS * (attempt + 1))
        return self._count(await self.talker.reply(request))

    def _count(self, reply: Reply) -> Reply:
        self.spent += reply.cost_usd
        return reply


class _MeteredJudge:
    """The reply checks' judge, with what it cost added up."""

    def __init__(self, judge: StructuredModel) -> None:
        self.judge, self.spent = judge, 0.0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        got = await self.judge.extract(system, user, schema)
        self.spent += got.cost_usd
        return got


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
            recorded = plan.rebuilt.get((f.id, v.label), plan.requests.get(f.id))
            talker = _Metered(models.talker_for(v.model, v.effort))
            judge = _MeteredJudge(models.judge)
            try:
                drawn = await draw(f, v, recorded, talker, judge)
            except Exception:
                drawn = None  # a provider that kept failing costs one sample, not the run
            if (v.model or "").endswith(":free"):
                await asyncio.sleep(FREE_SPACING_SECONDS)  # OpenRouter allows 20 a minute
            cost = talker.spent + judge.spent
            results.spent += cost
            if drawn is None:
                cell.skipped += 1
                return
            reply, req = drawn.reply, drawn.request
            verdicts: list[Verdict] = []
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
            cell.samples.append(
                Sample(reply.text, tuple(verdicts), reply.latency_ms, cost, drawn.redrawn)
            )

    await asyncio.gather(
        *(one(f, v) for f in plan.fixtures for v in plan.variants for _ in range(plan.samples))
    )
    return results
