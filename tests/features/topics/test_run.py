from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from companion.core.basics import name_belief
from companion.core.extractor import Extraction
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Frame, Json, Speaker, TurnId, Utterance, UtteranceId
from companion.features.topics.logic import SPENT
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


class Spent(Judge):
    """Reads every message as ordinary, and says the topic is spent whenever it is asked."""

    def __init__(self) -> None:
        super().__init__()
        self.asked = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"spent"}:
            self.asked += 1
            return Extraction({"spent": True}, "j", 0.0, 1)
        return await super().extract(system, user, schema)


class Asker(Talker):
    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text="ooh what sauce?", model="fake", latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "sam",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    s.append_utterance(said)
    s.insert_belief(name_belief(said, "Sam", "b1", said.at))
    return s


async def _say(
    store: Store, at: datetime, text: str = "honey mustard", judge: Spent | None = None
) -> str:
    talker = Asker()
    convo = Conversation(store, talker, PREFIX, REL, judge=judge or Spent())
    await handle(convo, SESSION, text, "t", at)
    return talker.seen[0].card


def _moves(store: Store) -> int:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 80)}
    return sum(d.reason == SPENT for t in turns for d in store.decisions_for_turn(REL, t))


async def test_a_spent_topic_gets_one_move_then_not_again_for_ten_of_their_messages(
    store: Store,
) -> None:
    assert "run its course" not in await _say(store, NOW)  # nothing asked before it yet
    store.append_utterance(
        Utterance(
            UtteranceId("c1"),
            REL,
            SESSION,
            TurnId("tc"),
            Speaker.COMPANION,
            "what sauce?",
            Frame.REAL,
            "t",
            NOW + timedelta(seconds=30),
        )
    )
    assert "run its course" in await _say(store, NOW + timedelta(minutes=1))
    for i in range(2, 11):
        assert "run its course" not in await _say(store, NOW + timedelta(minutes=i))
    assert "run its course" in await _say(store, NOW + timedelta(minutes=11))
    assert _moves(store) == 2


async def test_a_long_message_or_a_question_of_theirs_asks_no_judge(store: Store) -> None:
    judge = Spent()
    await _say(store, NOW, "honey mustard")  # leaves a companion question in the history
    judge.asked = 0
    await _say(store, NOW + timedelta(minutes=1), "thin ones, what about you?", judge)
    await _say(store, NOW + timedelta(minutes=2), "i got the job today and i am so happy", judge)
    assert judge.asked == 0
