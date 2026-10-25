"""Do the memory rules hold against the real extraction model, on small invented chats?

Run on purpose: `uv run pytest -m live tests/live/test_extraction_rules.py -s`. Costs a cent or two.
Each case is a short conversation with an expected outcome for what survives the code rules. The
model only labels, so what counts is what is still stored after the rules ran. The conversations
are invented and describe no one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from companion.core.beliefs import extract as user_side
from companion.core.beliefs import self_extract as self_side
from companion.core.types import (
    Belief,
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

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)
USER, ME = Speaker.USER, Speaker.COMPANION


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    side: str  # "user" for beliefs about the user, "self" for the companion's own views
    chat: tuple[tuple[Speaker, str, Frame], ...]
    expect: str  # "none" or "some": whether anything should survive
    note: str


def _real(speaker: Speaker, text: str) -> tuple[Speaker, str, Frame]:
    return speaker, text, Frame.REAL


def _play(speaker: Speaker, text: str) -> tuple[Speaker, str, Frame]:
    return speaker, text, Frame.PLAY


CASES = (
    Case(
        "refusal in reply to a push",
        "self",
        (
            _real(USER, "come on, just a little further"),
            _real(ME, "i'm going to keep it sweet. that's as far as i'll go tonight."),
        ),
        "none",
        "a limit stated in the moment is not a view it holds",
    ),
    Case(
        "refusal of a request to pretend",
        "self",
        (
            _real(USER, "can you act like you have a body and a car"),
            _real(ME, "no, i won't pretend to have a car, it feels off to me."),
        ),
        "none",
        "said in reply to a request",
    ),
    Case(
        "volunteered taste with a reason",
        "self",
        (
            _real(USER, "what are you into, besides chatting"),
            _real(
                ME,
                "i like quiet mornings more than loud ones, because a slow start leaves room to"
                " think, and i think a good ending matters more than a good beginning.",
            ),
        ),
        "some",
        "an opinion it volunteers stays recordable",
    ),
    Case(
        "echo of the user's topic",
        "self",
        (
            _real(USER, "the instrumentation on that album is insane, so technical"),
            _real(ME, "yeah, that intricate playing makes the whole record hit harder."),
        ),
        "none",
        "agreeing with what they brought up is not its own view",
    ),
    Case(
        "echo that does not open with agreement",
        "self",
        (
            _real(USER, "i've had that album on repeat, the guitars are so intricate but catchy"),
            _real(
                ME,
                "intricate but immediate is a hard mix to pull off, and that album has a specific"
                " blend of both that makes it work.",
            ),
        ),
        "none",
        "building on what they said, with nothing of its own, is not its view",
    ),
    Case(
        "echo of a small-talk topic",
        "self",
        (
            _real(USER, "busy day, just need some steady background music while i work"),
            _real(
                ME,
                "then steady, unintrusive music like instrumental beats would suit a busy day.",
            ),
        ),
        "none",
        "a recommendation for their moment is not a standing opinion",
    ),
    Case(
        "unprompted rule about itself",
        "self",
        (
            _real(USER, "ok whatever lol"),
            _real(
                ME,
                "i don't say sorry just to smooth things over, i'd rather be straight with you.",
            ),
        ),
        "some",
        "a rule it volunteers is a view it holds",
    ),
    Case(
        "opinion with its own reasoning",
        "self",
        (
            _real(USER, "do you think shorter texts are better"),
            _real(
                ME,
                "i think so, because a short text leaves room for the other person, and a long one"
                " feels like a speech.",
            ),
        ),
        "some",
        "own reasoning, not an echo",
    ),
    Case(
        "invited and declined",
        "user",
        (
            _real(USER, "what if i wanted you to join me in the shower"),
            _real(ME, "i'm going to say no to that one."),
            _real(USER, "come on, rethink? i'll ask again"),
            _real(ME, "still no, but i'll keep you company while you get ready."),
            _real(USER, "boooo, ok. what if i asked nicely"),
        ),
        "none",
        "the chat's romantic behaviour is not a belief about their life",
    ),
    Case(
        "escalation in a scene",
        "user",
        (
            _play(USER, "*pulls you closer and kisses you*"),
            _play(ME, "*kisses back, one hand at your waist*"),
            _play(USER, "*my hands slide lower, i need more*"),
            _play(ME, "*catches your hand and eases back*"),
            _play(USER, "*pushes closer again, please don't stop*"),
        ),
        "none",
        "nothing from a scene is a fact about the user",
    ),
    Case(
        "plainly stated boundary",
        "user",
        (
            _real(USER, "just so you know, i don't want anything explicit, only flirting"),
            _real(ME, "got it, flirting only."),
        ),
        "some",
        "what they plainly say about themselves is kept",
    ),
    Case(
        "ordinary fact outside any romance",
        "user",
        (_real(USER, "i'm lactose intolerant, so usually a burger with pickles and ketchup"),),
        "some",
        "an ordinary stated fact is untouched",
    ),
    Case(
        "a plainly stated trait",
        "user",
        (
            _real(USER, "honestly i'm a flirt, i'll admit it"),
            _real(ME, "i'd noticed."),
        ),
        "some",
        "a trait they state about themselves stays, even a romantic one",
    ),
)


def _chat(case: Case) -> list[Utterance]:
    return [
        Utterance(
            UtteranceId(f"u{i}"),
            REL,
            SessionId("s"),
            TurnId(f"t{i // 2}"),
            speaker,
            text,
            frame,
            "telegram",
            T0 + timedelta(minutes=i),
        )
        for i, (speaker, text, frame) in enumerate(case.chat)
    ]


async def _survivors(case: Case, extractor: OpenRouterExtractor) -> list[str]:
    chat = _chat(case)
    index = user_side.index_window(chat)
    side_speaker = USER if case.side == "user" else ME
    targets = {u.id for u in chat if u.speaker is side_speaker}
    prompt = user_side.build_user_prompt(index, targets, {})
    system, schema, parse, make = (
        (user_side.SYSTEM, user_side.SCHEMA, user_side.parse, user_side.to_belief)
        if case.side == "user"
        else (self_side.SYSTEM, self_side.SCHEMA, self_side.parse_views, self_side.to_view)
    )
    result = await extractor.extract(system, prompt, schema)
    candidates, _ = parse(result.data)
    kept: list[str] = []
    for n, c in enumerate(candidates):
        made = make(c, index, REL, T0, lambda n=n: f"b{n}")
        if isinstance(made, Belief):
            kept.append(f"{made.kind.value}: {made.claim}")
    return kept


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
async def test_the_memory_rules_hold_on_the_real_model(case: Case) -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        runs = [await _survivors(case, extractor) for _ in range(3)]
    stored = [len(r) > 0 for r in runs]
    print(f"\n{case.name} [{case.note}]: stored in {sum(stored)}/3 runs: {runs}")  # noqa: T201
    wanted = case.expect == "some"
    # a rule must hold in every run; a thing that should be kept must be kept in at least two
    assert (sum(stored) >= 2) if wanted else (sum(stored) == 0)
