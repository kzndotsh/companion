from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import DecisionKind, RelationshipId, SessionId
from companion.loops.fast import Conversation
from companion.models.anthropic import AnthropicTalker
from companion.models.openrouter import OpenRouterTalker
from companion.store.sqlite import replay as store_replay
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class FakeTalker:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text=self.texts.pop(0), model="fake", latency_ms=5)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_turns_are_logged_and_replay_matches(store: Store, tmp_path: Path) -> None:
    talker = FakeTalker("hey", "couldn't sleep either?", "ha, fair")
    convo = Conversation(store, talker, PREFIX, REL)
    for i, text in enumerate(["morning", "up early", "yeah"]):
        await convo.handle(SESSION, text, "test", NOW + timedelta(minutes=i))
    assert len(talker.seen[2].messages) == 5  # two earlier exchanges plus the new message
    store.close()
    for turn_id in _turn_ids(tmp_path / "rel.sqlite"):
        report = store_replay.replay_file(tmp_path / "rel.sqlite", turn_id)
        assert report.matched
        assert [d.kind for d in report.decisions] == [DecisionKind.POLICY]


async def test_empty_model_reply_is_logged_not_sent(store: Store, tmp_path: Path) -> None:
    convo = Conversation(store, FakeTalker(""), PREFIX, REL)
    assert await convo.handle(SESSION, "hello", "test", NOW) == ""
    store.close()
    report = store_replay.replay_file(
        tmp_path / "rel.sqlite", _turn_ids(tmp_path / "rel.sqlite")[0]
    )
    assert [d.kind for d in report.decisions] == [DecisionKind.DO_NOTHING]


def _turn_ids(db: Path) -> list[str]:
    import sqlite3  # noqa: PLC0415

    with sqlite3.connect(db) as c:
        return [r[0] for r in c.execute("SELECT turn_id FROM turn_requests ORDER BY at")]


def _request() -> TalkerRequest:
    from companion.core.prompt.request import build_request  # noqa: PLC0415

    return build_request(PREFIX, [], "hi")


async def test_anthropic_body_has_cached_system_and_no_thinking() -> None:
    sent: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        sent.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "m",
                "content": [{"type": "text", "text": " hi "}],
                "usage": {"input_tokens": 7, "cache_read_input_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reply = await AnthropicTalker("k", client).reply(_request())
    assert reply.text == "hi"
    assert reply.cache_read_tokens == 5
    assert "thinking" not in sent
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}  # type: ignore[index]


async def test_openrouter_pins_provider_and_disables_reasoning() -> None:
    sent: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        sent.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "anthropic/claude-haiku-4.5",
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 9, "prompt_tokens_details": {"cached_tokens": 4}},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reply = await OpenRouterTalker("k", client).reply(_request())
    assert reply.text == "hi"
    assert reply.cache_read_tokens == 4
    assert sent["provider"] == {"order": ["Anthropic"], "allow_fallbacks": False}
    assert sent["reasoning"] == {"enabled": False}
