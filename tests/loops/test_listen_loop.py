from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.ack import Reaction
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
    def __init__(self) -> None:
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text="ok", model="fake", latency_ms=1)


class Judge:
    """Answers the listening schema with the labels given, and every other schema with nothing."""

    def __init__(self, labels: Json = None, *, fail: bool = False) -> None:
        self.labels = labels
        self.fail = fail

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        properties = schema["properties"]
        assert isinstance(properties, dict)
        if "severity" not in properties:
            return Extraction(data=None, model="j", cost_usd=0.0, latency_ms=1)
        if self.fail:
            msg = "provider down"
            raise RuntimeError(msg)
        return Extraction(data=self.labels, model="j", cost_usd=0.0, latency_ms=1)


def _labels(severity: int, stance: str = "listening", *, vague: bool = False) -> Json:
    return {"severity": severity, "stance": stance, "vague": vague, "medical": False}


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _ask(store: Store, judge: Judge, text: str = "my boss ignored me again today") -> Talker:
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, judge=judge)
    await convo.handle(SESSION, text, "test", NOW)
    return talker


async def test_a_listening_note_reaches_the_system_block_and_never_the_message(
    store: Store,
) -> None:
    talker = await _ask(store, Judge(_labels(1)))
    request = talker.seen[0]
    assert "They are sharing or venting" in request.card
    assert "They are sharing or venting" not in request.messages[-1].content
    assert request.messages[-1].content == "my boss ignored me again today"


async def test_the_labels_are_logged_as_a_decision_with_the_scorer(store: Store) -> None:
    await _ask(store, Judge(_labels(2, vague=True)))
    [turn] = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 5)}
    reasons = [d.reason for d in store.decisions_for_turn(REL, turn)]
    assert any(r == "listening note added: severity 2, listening, vague" for r in reasons)
    detail = next(d.detail for d in store.decisions_for_turn(REL, turn) if "listening" in d.reason)
    assert detail is not None
    assert detail["labels"] == {"severity": 2, "stance": "listening", "vague": True}
    assert detail["scorer"] == "j"


@pytest.mark.parametrize("labels", [_labels(3), _labels(1, "inviting"), _labels(0, "other"), None])
async def test_no_note_for_acute_inviting_other_or_an_unreadable_answer(
    store: Store, labels: Json
) -> None:
    talker = await _ask(store, Judge(labels))
    assert "[They are" not in talker.seen[0].card


async def test_a_failing_judge_means_no_note_and_the_reply_still_goes_out(store: Store) -> None:
    talker = await _ask(store, Judge(fail=True))
    assert len(talker.seen) == 1
    assert "[They are" not in talker.seen[0].card


async def test_no_judge_at_all_changes_nothing(store: Store) -> None:
    talker = Talker()
    await Conversation(store, talker, PREFIX, REL).handle(SESSION, "rough week", "test", NOW)
    assert "[They are" not in talker.seen[0].card


async def test_acute_is_logged_as_having_no_crisis_path(store: Store) -> None:
    await _ask(store, Judge(_labels(3)))
    [turn] = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 5)}
    assert any("no crisis path" in d.reason for d in store.decisions_for_turn(REL, turn))


async def test_listen_off_never_asks_the_judge_and_adds_no_note(store: Store) -> None:
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, judge=Judge(_labels(2)), listen=False)
    await convo.handle(SESSION, "rough week", "test", NOW)
    assert "[They are" not in talker.seen[0].card


SHORT_NOTE = "Their message was short"


@pytest.mark.parametrize(("severity", "capped"), [(0, True), (1, True), (2, False), (3, False)])
async def test_a_serious_or_acute_message_gets_no_length_cap(
    store: Store, severity: int, *, capped: bool
) -> None:
    talker = await _ask(store, Judge(_labels(severity)), text="my mom is in the hospital")
    assert (SHORT_NOTE in talker.seen[0].card) is capped


class AckAndListen:
    """Calls every short message a sure acknowledgement, and labels each message with the next
    severity in the list."""

    def __init__(self, *severities: int) -> None:
        self.severities = list(severities)

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        properties = schema["properties"]
        assert isinstance(properties, dict)
        if "kind" in properties and "emoji" in properties:
            data: Json = {"kind": "ack", "confidence": 0.9, "emoji": "👍"}
        elif "severity" in properties:
            data = _labels(self.severities.pop(0))
        else:
            data = None
        return Extraction(data=data, model="j", cost_usd=0.0, latency_ms=1)


@pytest.mark.parametrize(("severity", "reacted"), [(0, True), (1, True), (2, False), (3, False)])
async def test_after_a_serious_message_a_bare_thanks_gets_words_not_an_emoji(
    store: Store, severity: int, *, reacted: bool
) -> None:
    convo = Conversation(store, Talker(), PREFIX, REL, judge=AckAndListen(severity, 0))
    await convo.handle(SESSION, "my mom is in the hospital", "test", NOW)
    answer = await convo.handle(SESSION, "thanks", "test", NOW + timedelta(minutes=1))
    assert isinstance(answer, Reaction) is reacted
