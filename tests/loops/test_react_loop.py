from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.ack import ReactAndReply, Reaction
from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId
from companion.loops.conversation import Conversation
from companion.loops.fast import handle
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
FUNNY: Json = {"tone": "funny", "confidence": 0.95, "emoji": "😁"}


class Talker:
    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        return Reply(text="ha, fair", model="fake", latency_ms=5)


class Judge:
    """Answers the reaction question only. The ack and frame judges get nothing useful."""

    def __init__(self, data: Json, *, fail: bool = False) -> None:
        self.data = data
        self.fail = fail

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        if self.fail:
            msg = "provider down"
            raise RuntimeError(msg)
        wanted = "tone" in schema["properties"]  # type: ignore[operator]
        return Extraction(
            data=self.data if wanted else None, model="judge", cost_usd=0.0, latency_ms=1
        )


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _say(store: Store, judge: Judge | None, texts: list[str]) -> list[object]:
    convo = Conversation(store, Talker(), PREFIX, REL, judge=judge)
    return [
        await handle(convo, SESSION, text, "test", NOW + timedelta(minutes=i))
        for i, text in enumerate(texts)
    ]


async def test_a_funny_message_gets_a_reaction_and_a_reply(store: Store) -> None:
    [out] = await _say(store, Judge(FUNNY), ["I just named my plant after my ex"])
    assert out == ReactAndReply(Reaction("😁"), "ha, fair")


async def test_every_judgement_is_logged_with_a_reason_written_by_code(store: Store) -> None:
    await _say(store, Judge(FUNNY), ["I just named my plant after my ex"])
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [
        d.reason for d in store.decisions_for_turn(REL, turn) if d.reason.startswith("react")
    ]
    assert reasons == ["reacted 😁 alongside the reply: judged funny at 0.95"]


async def test_a_second_reaction_waits_for_a_gap(store: Store) -> None:
    outs = await _say(store, Judge(FUNNY), ["one", "two", "three", "four"])
    reacted = [isinstance(o, ReactAndReply) for o in outs]
    assert reacted == [True, False, False, True]


async def test_a_failing_judge_means_a_plain_reply(store: Store) -> None:
    [out] = await _say(store, Judge(FUNNY, fail=True), ["I just named my plant after my ex"])
    assert out == "ha, fair"


async def test_no_judge_means_a_plain_reply(store: Store) -> None:
    [out] = await _say(store, None, ["I just named my plant after my ex"])
    assert out == "ha, fair"


async def test_a_plain_judgement_means_a_plain_reply(store: Store) -> None:
    plain: Json = {"tone": "plain", "confidence": 0.99, "emoji": "😁"}
    [out] = await _say(store, Judge(plain), ["what time is it"])
    assert out == "ha, fair"
