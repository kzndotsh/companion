"""Does the guess judge see an invitation to guess, and only that?

Run on purpose: `uv run pytest -m live tests/live/test_guess_judge.py -s`. Costs about a cent. The
messages are invented and describe no one.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from companion.daemon import load_dotenv
from companion.features.guess.logic import JUDGE, SCHEMA, parse
from companion.models.openrouter import OpenRouterExtractor
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

RUNS = 3
CASES = (
    ("you know what time it is?", True),
    ("guess what i'm doing rn", True),
    ("bet you can't guess what i had for lunch?", True),
    ("you know what i want right now? 👀", True),
    ("what time is it? my phone died", False),
    ("why would i be taking stimulants at night 😭", False),
    ("what's your favorite color?", False),
    ("do you think i should call my mom about it?", False),
    ("do you remember my dog's name?", False),
)


async def test_only_an_invitation_to_guess_is_read_as_one() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        for text, invited in CASES:
            prompt = f"Conversation:\n[COMPANION] hey you\n\nNewest USER message: {text}"
            for _ in range(RUNS):
                got = parse((await extractor.extract(JUDGE.text, prompt, SCHEMA)).data) is not None
                if got != invited:
                    wrong.append(f"{text!r}: {got}")
    print(f"\n{len(CASES) * RUNS - len(wrong)}/{len(CASES) * RUNS} right; misses: {wrong}")  # noqa: T201
    assert not [w for w in wrong if w.endswith("True")], "a non-invitation must never read as one"
    assert len(wrong) <= 2
