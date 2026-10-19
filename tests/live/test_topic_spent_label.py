"""Does the topic judge see a small topic run its course, and only then?

Run on purpose: `uv run pytest -m live tests/live/test_topic_spent_label.py -s`. Costs about a cent.
Each case is a short invented chat. A topic narrowed to smaller and smaller details and answered
in a word or two is spent; affection, flirting, a goodbye, news, a question or a topic just opening
up is not. The messages describe no one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from companion.core.mood import held_because
from companion.core.topics import JUDGE, SCHEMA, judge_prompt, likely, parse
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

RUNS = 3
U, C = "USER", "COMPANION"
NARROW_LUNCH = (
    (C, "what'd you have for lunch?"),
    (U, "a sandwich"),
    (C, "ooh what kind?"),
    (U, "turkey"),
    (C, "toasted or just plain?"),
)
NARROW_SNACK = (
    (C, "what's your go-to snack?"),
    (U, "chips"),
    (C, "which flavor?"),
    (U, "salt and vinegar"),
    (C, "the thin crispy kind or the thick ones?"),
)
SAUCE = (
    (C, "what sauce do you get with nuggets?"),
    (U, "honey mustard"),
    (C, "honey mustard makes the whole plate look fancier than it is 😌"),
)


@dataclass(frozen=True, slots=True)
class Case:
    chat: tuple[tuple[str, str], ...]
    text: str
    spent: bool


CASES = (
    Case(NARROW_LUNCH, "plain lol", spent=True),
    Case(NARROW_SNACK, "thin ones", spent=True),
    Case(SAUCE, "hehe true", spent=False),  # after a remark, not a question: never asked
    Case(NARROW_LUNCH, "just plain, nothing special", spent=True),
    Case(((C, "only for you, pretty girl ❤️"),), "cutiepie", spent=False),
    Case(((C, "come here then 😏"),), "make me", spent=False),
    Case(((C, "sleep well, talk tomorrow!"),), "night night", spent=False),
    Case(SAUCE[:1], "honey mustard", spent=False),  # one question in: still opening up
    Case(SAUCE[:1], "lol honey mustard. oh also i got the job!!", spent=False),
    Case(((C, "how was the trip?"),), "honestly amazing", spent=False),
)


def _utt(i: int, who: str, text: str) -> Utterance:
    speaker = Speaker.USER if who == U else Speaker.COMPANION
    return Utterance(
        UtteranceId(f"u{i}"),
        RelationshipId("r"),
        SessionId("s"),
        TurnId(f"t{i}"),
        speaker,
        text,
        Frame.REAL,
        "test",
        datetime(2026, 10, 19, 15, i, tzinfo=UTC),
    )


async def test_a_spent_topic_is_seen_and_nothing_else_is() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    right = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, "anthropic/claude-haiku-5.5")
        for case in CASES:
            prior = [_utt(i, who, text) for i, (who, text) in enumerate(case.chat)]
            prompt = judge_prompt(prior, case.text)
            for _ in range(RUNS):
                spent = parse((await extractor.extract(JUDGE.text, prompt, SCHEMA)).data)
                total += 1
                # score what code would do: goodbyes and unlikely moments never reach the note
                leaving = held_because(severity=0, text=case.text, in_scene=False) is not None
                if (spent and likely(prior, case.text) and not leaving) == case.spent:
                    right += 1
                else:
                    wrong.append(f"{case.text!r}: {spent}")
    print(f"\n{right}/{total} right; misses: {wrong}")  # noqa: T201
    false_alarms = [w for w in wrong if w.endswith("True")]
    assert not false_alarms, "affection, flirting, goodbyes, news and questions must not trigger it"
    assert right / total >= 0.8
