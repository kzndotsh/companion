"""Does the reader of what is happening with them now label messages right, on invented ones?

Run on purpose: `uv run pytest -m live tests/live/test_now_read.py -s`. Costs under a cent. A `soon`
read where nothing is coming would make the note claim something they never said; a missed `done`
would keep the note after it happened (ADR 0024). The messages are invented and describe no one.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from companion.core.turn.now import PROMPT, SCHEMA, Phase, parse, reader_input
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
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

S, L, B, D, N = Phase.SOON, Phase.LEAVING, Phase.BACK, Phase.DONE, Phase.NONE
CASES: tuple[tuple[str, Phase] | tuple[str, Phase, str], ...] = (
    ("soon lol", S, "are you making coffee?"),
    ("you'll have voice mode soon :3", N),
    ("i need to go to the dentist sometime", N),
    ("getting dinner soon, guess what i ordered", S),
    ("pizza should be here in like 20 min", S),
    ("gonna shower in a bit", S),
    ("laundry's almost done then i'm all yours", S),
    ("brb gonna go shower", L),
    ("ok gotta run to the store, text you after", L),
    ("going to make dinner now, back in a bit", L),
    ("back!", B),
    ("ok i'm back, that took forever", B),
    ("food's here!!", D),
    ("just finished eating, so full", D),
    ("showered, feel human again", D),
    ("i might go to japan next year", N),
    ("i love sushi so much", N),
    ("i had pancakes this morning", N),
    ("my sister is visiting next week", N),
)
RUNS = 2


def _companion(text: str) -> Utterance:
    return Utterance(
        UtteranceId("c"),
        RelationshipId("r"),
        SessionId("s"),
        TurnId("t"),
        Speaker.COMPANION,
        text,
        Frame.REAL,
        "test",
        datetime(2026, 10, 25, tzinfo=UTC),
    )


async def test_what_is_happening_with_them_now_is_read_right() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    right = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        for case in CASES:
            text, want = case[0], case[1]
            said = reader_input([_companion(case[2])] if len(case) > 2 else [], text)
            for _ in range(RUNS):
                got = parse((await extractor.extract(PROMPT.text, said, SCHEMA)).data)
                phase = got.phase if got is not None else None
                total += 1
                if phase is want:
                    right += 1
                else:
                    wrong.append(f"{text!r}: {phase} (want {want})")
    print(f"\n{right}/{total} right; misses: {wrong}")  # noqa: T201
    false_soon = [w for w in wrong if ": soon (want none)" in w]
    assert not false_soon, "nothing coming must not read as something coming"
    assert right / total >= 0.8
