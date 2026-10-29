"""Does the memory pair judge read a corrected or changed fact as a conflict, and a pair that can
both be true as not one (J11)? A pair read as a conflict all three times becomes a question for the
owner in `companion memory review`, so a false alarm costs the owner a question, not a memory.

Run on purpose: `uv run pytest -m live tests/live/test_pair_conflicts.py -s`. Costs about a cent.
The memories are invented and describe no one.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from companion.core.types import Belief
from companion.daemon import load_dotenv
from companion.features.upkeep.reread.logic import (
    PAIR,
    PAIR_SCHEMA,
    Relation,
    pair_prompt,
    read_relation,
)
from companion.lib.vote import READS
from companion.models.openrouter import OpenRouterExtractor
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

CONFLICTS = (
    ("The user's dog is a pomeranian.", "The user's dog is a papillon and sheltie mix."),
    ("The user works as a barista.", "The user quit the barista job and now works at a bookstore."),
    ("The user lives in Ohio.", "The user moved to Denver last month."),
    (
        "The user plans to start a new job on 2026-10-12.",
        "The user started their new job on 2026-10-12.",
    ),
    ("The user is single.", "The user has a girlfriend named Mia."),
    ("The user is vegetarian.", "The user eats chicken most days now."),
    ("The user's favourite colour is green.", "The user's favourite colour is purple, not green."),
    ("The user has two cats.", "The user has one cat since the older one died."),
    ("The user is 24 years old.", "The user is 26 years old."),
    ("The user is learning Spanish.", "The user gave up on learning Spanish."),
    ("The user does not drink alcohol.", "The user drinks wine on weekends."),
    ("The user's sister is named Emma.", "The user's sister is named Emily, not Emma."),
    ("The user hates running.", "The user has started running and enjoys it."),
    ("As of 2026-10-01 the user is unemployed.", "As of 2026-10-15 the user works at a warehouse."),
)
BOTH_TRUE = (
    (
        "As of 2026-10-15 the user has been feeling lonely.",
        "As of 2026-10-20 the user has been feeling low.",
    ),
    ("The user finds their phone battery drains fast.", "The user bought a new phone charger."),
    ("The user loves dogs.", "The user is allergic to cats."),
    ("The user likes horror movies.", "The user gets scared easily at night."),
    ("The user wants to move to Japan someday.", "The user lives in Ohio."),
    ("The user likes coffee.", "The user drinks tea in the evening."),
    ("The user works night shifts.", "The user likes slow mornings on their days off."),
    ("The user feels confident at work.", "The user feels insecure about their looks."),
    ("The user has a dog named Max.", "The user's neighbour has a dog named Bella."),
    ("The user plans to visit their mom on Sunday.", "The user visited their dad last weekend."),
    ("The user is tired of being anxious.", "As of 2026-10-20 the user has been feeling anxious."),
    ("The user wants to quit smoking.", "The user smoked a cigarette on 2026-10-19."),
    ("The user loves their job.", "The user is stressed by their boss."),
    (
        "The user dislikes posting on social media.",
        "The user feels pressure to post online to find work.",
    ),
    ("The user is a night owl.", "The user woke up early on 2026-10-19 for an appointment."),
    ("The user is vegetarian.", "The user loves the smell of bacon."),
    ("The user is single.", "The user had a date on Friday 2026-10-16."),
    ("The user has a dog named Max.", "The user owns a dog called Max."),
    ("The user likes indie music.", "The user listens mostly to indie and alt music."),
)
CONFLICT = {Relation.REPLACES, Relation.CONTRADICTS}


async def _flagged(extractor: OpenRouterExtractor, older: Belief, newer: Belief) -> bool:
    async def one() -> str | None:
        return read_relation(
            (await extractor.extract(PAIR.text, pair_prompt(older, newer), PAIR_SCHEMA)).data
        )

    reads = await asyncio.gather(*(one() for _ in range(READS)))
    return all(r in CONFLICT for r in reads)


async def test_a_changed_fact_is_a_conflict_and_two_true_things_are_not(
    belief: Callable[..., Belief],
) -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)

        async def flagged(pair: tuple[str, str]) -> bool:
            return await _flagged(extractor, belief(claim=pair[0]), belief(claim=pair[1]))

        caught = await asyncio.gather(*(flagged(p) for p in CONFLICTS))
        alarms = await asyncio.gather(*(flagged(p) for p in BOTH_TRUE))
    missed = [p[1] for p, hit in zip(CONFLICTS, caught, strict=True) if not hit]
    false = [p[1] for p, hit in zip(BOTH_TRUE, alarms, strict=True) if hit]
    summary = f"caught {sum(caught)}/{len(CONFLICTS)}, false alarms {sum(alarms)}/{len(BOTH_TRUE)}"
    print(f"\n{summary}: {false}")  # noqa: T201
    assert len(missed) <= 1, missed
    assert len(false) <= 3, false
