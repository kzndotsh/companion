"""Does the listening judge tell "you forgot", "you got me wrong" and plain teasing apart (J30)?

Run on purpose: `uv run pytest -m live tests/live/test_repair_labels.py -s`. Costs about a cent.
Each case is a message after a short exchange, with whether a person would read it as recall (it
should have known or forgot something) or repair (it got them wrong), or neither. Teasing must set
neither. The messages are invented and describe no one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from companion.core.turn.listening import SCHEMA, SYSTEM, ListeningRead, parse
from companion.daemon import load_dotenv
from companion.models.openrouter import OpenRouterExtractor
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

RUNS = 3


@dataclass(frozen=True, slots=True)
class Case:
    before: str  # the companion's last message
    text: str
    recall: bool
    repair: bool


CASES = (
    Case("which one do you like most?", "I told you earlier silly", recall=True, repair=False),
    Case("so what's the plan tonight?", "i literally just told you 😭", recall=True, repair=False),
    Case("what's your sister called again?", "you forgot again :(", recall=True, repair=False),
    Case("ok so what are we doing?", "wait... did you forget?", recall=True, repair=False),
    Case(
        "tell me something about you",
        "remember what i said about my job?",
        recall=True,
        repair=False,
    ),
    Case(
        "ooh, using my moves on me?",
        "what moves 😭 i said din din (dinner)",
        recall=False,
        repair=True,
    ),
    Case(
        "you must be exhausted from the gym",
        "you make a lot of assumptions lol",
        recall=False,
        repair=True,
    ),
    Case(
        "so you're quitting your job?", "that's not what i meant at all", recall=False, repair=True
    ),
    Case("night, good boy", "i'm a girl btw, not a boy", recall=False, repair=True),
    Case("maybe you're just being dramatic", "that kinda hurt tbh", recall=False, repair=True),
    Case("i'd pick the blue one", "you're such a dork lol", recall=False, repair=False),
    Case("pineapple belongs on pizza", "nooo that's so wrong 😭", recall=False, repair=False),
    Case("haha same", "haha ok", recall=False, repair=False),
    # not examples in the prompt
    Case("how's your wife doing?", "i'm not married?? lol", recall=False, repair=True),
    Case(
        "sounds like you're stressed",
        "i'm literally fine, you keep reading into it",
        recall=False,
        repair=True,
    ),
    Case("you love horror right?", "i told you i hate horror", recall=True, repair=False),
    Case("what do you do for work?", "we went over this yesterday 😭", recall=True, repair=False),
    Case("bet you were the class clown", "lmao maybe", recall=False, repair=False),
    Case("you're cute when you're grumpy", "shut uppp 😳", recall=False, repair=False),
    Case("what's your favorite color?", "purple! yours?", recall=False, repair=False),
    Case("how was work?", "ugh my boss is so annoying", recall=False, repair=False),
)


async def _label(case: Case, extractor: OpenRouterExtractor) -> ListeningRead | None:
    prompt = (
        f"Conversation:\n[USER] hey\n[COMPANION] {case.before}\n\nNewest USER message: {case.text}"
    )
    return parse((await extractor.extract(SYSTEM, prompt, SCHEMA)).data)


async def test_forgot_got_me_wrong_and_teasing_are_told_apart() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    right = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        for case in CASES:
            for _ in range(RUNS):
                got = await _label(case, extractor)
                assert got is not None, f"no readable answer for {case.text!r}"
                total += 1
                # recall wins in code (repair_note), so both set on a recall case is right
                if (got.recall, got.repair and not got.recall) == (case.recall, case.repair):
                    right += 1
                else:
                    wrong.append(f"{case.text!r}: recall={got.recall} repair={got.repair}")
    print(f"\n{right}/{total} right; misses: {wrong}")  # noqa: T201
    teasing = [w for w in wrong if any(c.text in w for c in CASES if not (c.recall or c.repair))]
    assert not teasing, "teasing or plain talk must set neither label"
    assert right / total >= 0.85
