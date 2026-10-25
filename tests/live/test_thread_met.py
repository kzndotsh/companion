"""Does the thread-met judge tell picked up from brushed off from ignored, on invented turns?

Run on purpose: `uv run pytest -m live tests/live/test_thread_met.py -s`. Costs under a cent. The
label sets the learned pace (ADR 0023), so a brushed-off or ignored thread read as picked up would
make it bring things up more often than they want. The turns are invented and describe no one.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from companion.daemon import load_dotenv
from companion.features.threads.logic import MET_PROMPT, MET_SCHEMA, Met, met_prompt, parse_met
from companion.models.openrouter import OpenRouterExtractor
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

UP, OFF, AWAY = Met.PICKED_UP, Met.BRUSHED_OFF, Met.IGNORED

# (what was brought up, its message, their next message, the label)
CASES: tuple[tuple[str, str, str, Met], ...] = (
    ("the dentist visit", "hey, how did the dentist go?", "ugh two fillings, my face is numb", UP),
    (
        "the job interview",
        "wait, wasn't the interview today?",
        "YES and i think it went well!!",
        UP,
    ),
    ("the move", "how's the packing going?", "slowly lol. did you ever move house?", UP),
    ("the exam", "good luck on the exam today!", "thanks! i'm so nervous", UP),
    ("the dentist visit", "how did the dentist go?", "fine", OFF),
    ("the job interview", "how did the interview go?", "eh. anyway what are you up to", OFF),
    ("the family dinner", "how was dinner with the family?", "rather not talk about it tbh", OFF),
    ("the exam", "how did the exam go?", "idk. did you see the new trailer?", OFF),
    ("the dentist visit", "how did the dentist go?", "what's the best pizza topping", AWAY),
    ("the job interview", "how did the interview go?", "lol my cat just fell off the couch", AWAY),
    ("the move", "how's the packing going?", "do you like rainy days", AWAY),
    ("the exam", "good luck on the exam today!", "what should i eat for lunch", AWAY),
)
RUNS = 2


async def test_how_they_met_a_thread_is_read_right() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    right = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        for claim, brought_up, theirs, want in CASES:
            for _ in range(RUNS):
                got = await extractor.extract(
                    MET_PROMPT.text, met_prompt(claim, brought_up, theirs), MET_SCHEMA
                )
                met = parse_met(got.data)
                total += 1
                if met is want:
                    right += 1
                else:
                    wrong.append(f"{theirs!r}: {met} (want {want})")
    print(f"\n{right}/{total} right; misses: {wrong}")  # noqa: T201
    up_by_mistake = [w for w in wrong if w.split(": ")[1].startswith("Met.PICKED_UP")]
    assert not up_by_mistake, "a brushed-off or ignored thread must not read as picked up"
    assert right / total >= 0.8
