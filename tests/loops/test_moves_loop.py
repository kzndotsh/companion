from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId
from companion.loops.conversation import Conversation
from companion.loops.fast import handle
from companion.loops.moves import HabitMemory
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class Talker:
    def __init__(self) -> None:
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text=f"okay sweetheart {len(self.seen)}", model="fake", latency_ms=1)


class Judge:
    """Names one habit when asked about habits; says nothing useful to the other judges."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        if self.fail:
            msg = "provider down"
            raise RuntimeError(msg)
        wanted = "habits" in schema["properties"]  # type: ignore[operator]
        data: Json = (
            {"habits": [{"habit": 'calls them "sweetheart" in every reply', "replies": 5}]}
            if wanted
            else None
        )
        return Extraction(data=data, model="judge", cost_usd=0.0, latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _chat(store: Store, judge: Judge | None, n: int) -> Talker:
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, judge=judge)
    for i in range(n):
        await handle(convo, SESSION, f"message {i}", "test", NOW + timedelta(minutes=2 * i))
        if convo.habits.pending is not None:
            await convo.habits.pending
    return talker


async def test_a_found_habit_reaches_a_later_request_as_a_note(store: Store) -> None:
    talker = await _chat(store, Judge(), 7)
    assert "keep doing this" not in talker.seen[2].card
    assert 'calls them "sweetheart" in every reply' in talker.seen[-1].card
    assert "keep doing this" not in talker.seen[-1].messages[-1].content


async def test_the_check_is_logged_with_a_reason_written_by_code(store: Store) -> None:
    await _chat(store, Judge(), 6)
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [
        d.reason for d in store.decisions_for_turn(REL, turn) if d.reason.startswith("habit")
    ]
    assert reasons == ["habit check: 1 habits found in the last 6 replies"]


async def test_a_failing_judge_means_no_note(store: Store) -> None:
    talker = await _chat(store, Judge(fail=True), 7)
    assert "keep doing this" not in talker.seen[-1].messages[-1].content


async def test_no_judge_means_no_note(store: Store) -> None:
    talker = await _chat(store, None, 7)
    assert "keep doing this" not in talker.seen[-1].messages[-1].content


async def test_a_habit_is_dropped_after_a_couple_of_turns() -> None:
    memory = HabitMemory(["a"], 0)
    assert memory.note() is not None
    assert memory.note() is not None
    assert memory.note() is None


async def test_only_one_check_runs_at_a_time() -> None:
    memory = HabitMemory()
    release = asyncio.Event()

    async def slow() -> list[str]:
        await release.wait()
        return ["first"]

    async def other() -> list[str]:
        return ["second"]

    memory.start(slow())
    memory.start(other())  # dropped: one is still running
    release.set()
    assert memory.pending is not None
    await memory.pending
    assert memory.habits == ["first"]
