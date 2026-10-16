from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId
from companion.loops.fast import Conversation
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class Talker:
    def __init__(self, name: str) -> None:
        self.name = name
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text=f"{self.name} {len(self.seen)}", model=self.name, latency_ms=1)


class Judge:
    """Says every message that needs a frame is play; the other judges get an inert answer."""

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del user
        if "label the frame" in system:
            return Extraction({"frame": "play", "confidence": 0.95}, "j", 0.0, 1)
        return Extraction(None, "j", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _chat(store: Store, texts: list[str], scene: Talker | None) -> Talker:
    everyday = Talker("everyday")
    convo = Conversation(store, everyday, PREFIX, REL, judge=Judge(), scene_talker=scene)
    for i, text in enumerate(texts):
        await convo.handle(SESSION, text, "t", NOW + timedelta(minutes=i))
    return everyday


async def test_the_scene_talker_takes_over_once_a_scene_is_in_progress(store: Store) -> None:
    scene = Talker("scene")
    everyday = await _chat(
        store, ["let's pretend you're a knight", "*bows*", "and then what"], scene
    )
    assert len(everyday.seen) == 1  # the message that started the scene
    assert len(scene.seen) == 2


async def test_without_a_scene_talker_everyone_is_answered_by_the_everyday_one(
    store: Store,
) -> None:
    everyday = await _chat(store, ["let's pretend you're a knight", "*bows*", "and then?"], None)
    assert len(everyday.seen) == 3


async def test_ordinary_chat_never_reaches_the_scene_talker(store: Store) -> None:
    scene = Talker("scene")
    everyday = await _chat(store, ["i got a haircut", "it looks okay", "thanks"], scene)
    assert len(everyday.seen) == 3
    assert scene.seen == []


async def test_the_choice_is_logged_with_a_reason_written_by_code(store: Store) -> None:
    await _chat(store, ["let's pretend you're a knight", "*bows*"], Talker("scene"))
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [d.reason for d in store.decisions_for_turn(REL, turn)]
    assert "replied with the scene talker: a pretend scene is in progress" in reasons
