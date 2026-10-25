"""Does the plan reader mark a repeat as the same thing, and keep different plans apart?

Run on purpose: `uv run pytest -m live tests/live/test_loop_repeats.py -s`. Costs under a cent. A
thing told in two messages, or again a day later, must become one thread, or it is brought up
twice; two plans said together must stay two (ADR 0023, `system/openloops` v4). The chats are
invented and describe no one.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from companion.core.beliefs.extract import index_window
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
from companion.features.threads.logic import Thread
from companion.features.threads.run import extract_open_loops
from companion.models.openrouter import OpenRouterExtractor
from companion.store.sqlite.store import Store
from tests.live.models import JUDGE_MODEL

pytestmark = pytest.mark.live

REL = RelationshipId("r")
T0 = datetime(2026, 10, 20, 18, 0, tzinfo=UTC)
U, C = Speaker.USER, Speaker.COMPANION
RUNS = 2

# (name, a thread already open or None, the chat, how many new threads it should make)
CASES: tuple[tuple[str, str | None, tuple[tuple[Speaker, str], ...], int], ...] = (
    (
        "one thing over two messages",
        None,
        (
            (U, "the repair shop still hasn't said if they can fix my bike"),
            (C, "oh no, the waiting is the worst"),
            (U, "they said they'd call back friday"),
        ),
        1,
    ),
    (
        "two plans on one day",
        None,
        (
            (U, "dentist tomorrow morning, then my sister's birthday dinner tomorrow night"),
            (C, "busy day! dentist first, cake after"),
        ),
        2,
    ),
    (
        "again a day later",
        "waiting to hear if the shop can fix their bike",
        (
            (U, "still no call from the bike shop"),
            (C, "the waiting is so annoying"),
        ),
        0,
    ),
    (
        "something else beside it",
        "waiting to hear if the shop can fix their bike",
        (
            (U, "also my new desk gets delivered next week"),
            (C, "ooh a new desk!"),
        ),
        1,
    ),
)


def _chat(store: Store, lines: tuple[tuple[Speaker, str], ...], start: datetime) -> list[Utterance]:
    out: list[Utterance] = []
    for i, (who, text) in enumerate(lines):
        u = Utterance(
            UtteranceId(f"u{start.timestamp():.0f}-{i}"),
            REL,
            SessionId("s"),
            TurnId(f"t{start.timestamp():.0f}-{i}"),
            who,
            text,
            Frame.REAL,
            "test",
            start + timedelta(minutes=i),
        )
        store.append_utterance(u)
        out.append(u)
    return out


def _open(store: Store, claim: str) -> None:
    said = _chat(store, ((U, claim),), T0 - timedelta(days=1))[0]
    when = T0 + timedelta(days=2)
    store.add_open_loop(Thread("old", REL, claim, claim, said.id, when, 0, said.at))


async def test_repeats_become_one_thread_and_different_plans_stay_apart(tmp_path: Path) -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    wrong: list[str] = []
    right = total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, JUDGE_MODEL)
        for n, (name, existing, lines, want) in enumerate(CASES):
            for run in range(RUNS):
                store = Store(tmp_path / f"{n}-{run}.sqlite")
                if existing is not None:
                    _open(store, existing)
                chat = _chat(store, lines, T0)
                before = len(store.open_loops(REL))
                targets = {u.id for u in chat if u.speaker is U}
                when = (T0 + timedelta(minutes=10), UTC)
                await extract_open_loops(
                    store,
                    extractor,
                    REL,
                    index_window(chat),
                    targets,
                    when,
                    lambda r, d: None,
                    loose=True,  # as the bot runs (COMPANION_LOOP_NOTES=loose)
                )
                made = len(store.open_loops(REL)) - before
                total += 1
                if made == want:
                    right += 1
                else:
                    wrong.append(f"{name}: {made} (want {want})")
                store.close()
    print(f"\n{right}/{total} right; misses: {wrong}")  # noqa: T201
    assert right / total >= 0.75
