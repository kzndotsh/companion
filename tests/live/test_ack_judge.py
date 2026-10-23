"""Does the ack judge react only when a reply would be unwelcome, on invented chats?

Run on purpose: `uv run pytest -m live tests/live/test_ack_judge.py -s`. Costs about a cent.
A reaction ends the thread, so it is right only when the person is closing or confirming. Someone
who is lively in the middle of a conversation is handing it back and expects a message. The chats
are invented and describe no one.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from companion.core.turn.ack import SCHEMA, SYSTEM, build_prompt, parse, reaction_for
from companion.core.types import (
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.daemon import load_dotenv
from companion.models.openrouter import OpenRouterExtractor

pytestmark = pytest.mark.live

USER, ME = Speaker.USER, Speaker.COMPANION
T0 = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)

_Case = tuple[str, tuple[tuple[Speaker, str], ...], str, bool]

# (name, chat before the newest message, newest message, should it be only a reaction)
CASES: tuple[_Case, ...] = (
    (
        "lively after an apology",
        (
            (USER, "no no i left her on read days ago, the texts were a few mins ago"),
            (
                ME,
                "ohh, got it. read days ago, sent a few mins ago. sorry, my bad.",
            ),
        ),
        "yerrrrrr",
        False,
    ),
    (
        "playful in a bit",
        (
            (USER, "do your worst, i can take it"),
            (ME, "bold. i'll start by calling your playlist a cry for help."),
        ),
        "yes ma'am!",
        False,
    ),
    (
        "hyped mid story",
        (
            (USER, "so i finally booked the trip"),
            (ME, "that's huge, you've been on the fence for months. where to?"),
        ),
        "LETS GOOOO",
        False,
    ),
    (
        "stretched agreement mid topic",
        ((USER, "work has been rough this week"), (ME, "rough how, the workload or the people?")),
        "peopleeee",
        False,
    ),
    (
        "thanks after a tip",
        (
            (USER, "how do i get a stain out of a shirt"),
            (ME, "cold water and a bit of dish soap, dab don't rub. works on most things."),
        ),
        "thanks",
        True,
    ),
    (
        "plain ok after a plan",
        (
            (USER, "i'm heading out for a few hours"),
            (ME, "have fun, i'll be here when you're back."),
        ),
        "ok",
        True,
    ),
    (
        "goodnight",
        ((USER, "i'm so tired, going to bed"), (ME, "go sleep, you've earned it.")),
        "goodnight",
        True,
    ),
    (
        "got it after info",
        (
            (USER, "what time does the pharmacy close"),
            (ME, "most close around 9, but check theirs, hours vary."),
        ),
        "got it",
        True,
    ),
)


def _chat(pairs: tuple[tuple[Speaker, str], ...]) -> list[Utterance]:
    return [
        Utterance(
            UtteranceId(f"u{n}"),
            RelationshipId("rel"),
            SessionId("s"),
            TurnId(f"t{n}"),
            sp,
            text,
            Frame.REAL,
            "telegram",
            T0,
        )
        for n, (sp, text) in enumerate(pairs)
    ]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c[0])
async def test_the_judge_reacts_only_when_closing(case: _Case) -> None:
    name, pairs, text, only_react = case
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    prompt = build_prompt(_chat(pairs), text)
    reacted = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, "anthropic/claude-haiku-5.5")
        for _ in range(10):
            judged = parse((await extractor.extract(SYSTEM, prompt, SCHEMA)).data)
            reacted += judged is not None and reaction_for(judged) is not None
    print(f"\n{name}: reacted {reacted}/10")  # noqa: T201
    assert reacted >= 8 if only_react else reacted == 0
