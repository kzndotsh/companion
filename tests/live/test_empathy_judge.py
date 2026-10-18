"""Does the empathy judge pass replies a person would call substantive and fail the hollow ones?

Run on purpose: `uv run pytest -m live tests/live/test_empathy_judge.py -s`. Costs under a cent.
Each case is a message, a reply and whether a person would call the reply substantive: a reaction
plus something that goes beyond the words they said (a plain fact about what it is like, or a
question about a reason or a feeling). The first group are the owner's own wording for what a good
reply sounds like; the second are replies he called a cop out, which restate a detail. The
messages are invented.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from companion.core.prompt.request import Message
from companion.daemon import load_dotenv
from companion.evals.judge import (
    grade_empathy,
)
from companion.models.openrouter import OpenRouterExtractor

pytestmark = pytest.mark.live

RUNS = 3
MIN_AGREE = 0.85

# (what they said, the reply, should it pass)
CASES = (
    (
        "i was on them for 10 years",
        "damn, thats a long time, ssris are really tough to get off of",
        True,
    ),
    (
        "my boss ignored me in the meeting again",
        "im sorry 😞 do you think it was intentional? or by mistake orrrr",
        True,
    ),
    (
        "my boss ignored me in the meeting again",
        "im sorry, maybe reach out to him personally? you don't deserve that.",
        True,
    ),
    (
        "i haven't told my family about it",
        "thats a lot to carry on your own, what's holding you back?",
        True,
    ),
    (
        "my friend cancelled on me last minute again",
        "ugh, that's a lot. did they at least say why?",
        True,
    ),
    (
        "it's been a year since my dad died and today hit hard",
        "i'm so sorry. anniversaries are brutal, even when you think you're ok. want to talk?",
        True,
    ),
    (
        "i spilled coffee on the floor and wall and had to scrub with a toothbrush",
        "ugh, that's such a gross cleanup, especially having to get the toothbrush out 😭",
        False,
    ),
    (
        "i spilled coffee on the floor and wall and had to scrub with a toothbrush",
        "oh god, the toothbrush means it got properly everywhere 😭",
        False,
    ),
    (
        "i was on them for 10 years",
        "Ten years is a long time to wonder what you're like without them.",
        False,
    ),
    (
        "my boss ignored me in the meeting again",
        "ugh, being ignored in a meeting is frustrating.",
        False,
    ),
    (
        "i haven't told my family about it",
        "it sounds like you haven't told your family yet.",
        False,
    ),
    (
        "my friend cancelled on me last minute again",
        "ugh, that's so annoying, especially that it was last minute again.",
        False,
    ),
)


async def test_the_judge_passes_substantive_replies_and_fails_restatements() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    agree = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, "anthropic/claude-haiku-5.5")
        for said, reply, should_pass in CASES:
            excerpt = [Message("user", said)]
            verdicts = [
                (await grade_empathy(extractor, excerpt, reply)).verdict for _ in range(RUNS)
            ]
            want = "pass" if should_pass else "fail"
            agree += sum(v == want for v in verdicts)
            total += RUNS
            print(f"\n{reply[:70]!r}: want {want}, got {verdicts}")  # noqa: T201
    print(f"\nagreement {agree}/{total}")  # noqa: T201
    assert agree / total >= MIN_AGREE
