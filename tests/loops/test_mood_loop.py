from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion import prompts
from companion.core.extractor import Extraction
from companion.core.mood import Source, State, effect
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId, TurnId
from companion.loops.fast import Conversation
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
NOW = datetime(2026, 10, 19, 17, 0, tzinfo=UTC)
PREFIX = build_prefix("You are a companion. " * 300)
PLAYFUL = prompts.get("notes/mood-playful").text
TENDER = prompts.get("notes/mood-tender").text


class Talker:
    def __init__(self, *, fail: bool = False) -> None:
        self.seen: list[TalkerRequest] = []
        self.fail = fail

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        if self.fail:
            msg = "talker down"
            raise RuntimeError(msg)
        return Reply(text="ha, fair", model="fake", latency_ms=1)


class Judge:
    """Rates every message at one severity and tone; `listening=False` makes that judge fail."""

    def __init__(self, severity: int = 0, tone: str = "plain", *, listening: bool = True) -> None:
        self.severity, self.tone, self.listening = severity, tone, listening

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        props = schema["properties"]
        assert isinstance(props, dict)
        data: Json = None
        if "severity" in props and self.listening:
            data = {
                "severity": self.severity,
                "stance": "other",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": False,
                "topic": "",
            }
        elif "tone" in props:
            data = {"tone": self.tone, "confidence": 0.9, "emoji": "🤣"}
        return Extraction(data=data, model="j", cost_usd=0.0, latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _say(
    store: Store, judge: Judge, mode: str, text: str = "lol ok", at: datetime = NOW
) -> Talker:
    talker = Talker()
    await Conversation(store, talker, PREFIX, REL, judge=judge, mood=mode).handle(
        SESSION, text, "test", at
    )
    return talker


def _mood_reasons(store: Store) -> list[str]:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 50)}
    return [
        d.reason
        for t in turns
        for d in store.decisions_for_turn(REL, t)
        if d.reason.startswith("mood:")
    ]


async def test_in_shadow_the_mood_is_logged_and_stored_but_never_shown(store: Store) -> None:
    store.add_mood_effects(REL, [effect(Source.TONE_FUNNY, 0.4, NOW, TurnId("t0"))])
    talker = await _say(store, Judge(), "shadow", "haha nooo!! 😂", NOW + timedelta(minutes=1))
    assert PLAYFUL not in talker.seen[0].card
    [reason] = _mood_reasons(store)
    assert reason.startswith("mood: playful") and reason.endswith("[shadow]")
    sources = {e.source for e in store.mood_effects_since(REL, NOW)}
    assert Source.ENERGY in sources


async def test_when_on_the_strongest_state_reaches_the_system_block(store: Store) -> None:
    store.add_mood_effects(REL, [effect(Source.TONE_FUNNY, 0.4, NOW, TurnId("t0"))])
    talker = await _say(store, Judge(), "on", at=NOW + timedelta(minutes=1))
    assert PLAYFUL in talker.seen[0].card
    assert PLAYFUL not in talker.seen[0].messages[-1].content


async def test_a_serious_turn_shows_no_mood_and_the_next_one_is_tender(store: Store) -> None:
    first = await _say(store, Judge(severity=2), "on", "my dad is in the hospital")
    assert TENDER not in first.seen[0].card
    assert [e.state for e in store.mood_effects_since(REL, NOW)] == [State.TENDER]
    second = await _say(store, Judge(), "on", "made pasta", NOW + timedelta(hours=2))
    assert TENDER in second.seen[0].card


async def test_a_turn_that_fails_adds_nothing_to_the_mood(store: Store) -> None:
    convo = Conversation(store, Talker(fail=True), PREFIX, REL, judge=Judge(), mood="on")
    with pytest.raises(RuntimeError):
        await convo.handle(SESSION, "haha yesss!! 😂", "test", NOW)
    assert store.mood_effects_since(REL, NOW - timedelta(days=1)) == []


async def test_without_a_listening_judgement_nothing_is_added(store: Store) -> None:
    await _say(store, Judge(listening=False), "on", "haha yesss!! 😂")
    assert store.mood_effects_since(REL, NOW - timedelta(days=1)) == []


async def test_off_works_nothing_out_and_logs_nothing(store: Store) -> None:
    await _say(store, Judge(), "off", "haha yesss!! 😂")
    assert store.mood_effects_since(REL, NOW - timedelta(days=1)) == []
    assert _mood_reasons(store) == []


async def test_their_previous_message_tone_moves_the_next_turn(store: Store) -> None:
    await _say(store, Judge(tone="funny"), "shadow", "you're ridiculous")
    await _say(store, Judge(), "shadow", "anyway", NOW + timedelta(minutes=2))
    sources = [e.source for e in store.mood_effects_since(REL, NOW)]
    assert Source.TONE_FUNNY in sources


async def test_a_goodbye_never_carries_the_mood_line(store: Store) -> None:
    store.add_mood_effects(REL, [effect(Source.TONE_FUNNY, 0.4, NOW, TurnId("t0"))])
    talker = await _say(store, Judge(), "on", "ok gotta go, ttyl", NOW + timedelta(minutes=1))
    assert PLAYFUL not in talker.seen[0].card
    assert _mood_reasons(store) == ["mood: held, they are leaving [on]"]


async def test_how_to_refer_to_them_is_pinned_after_the_clock_on_every_turn(store: Store) -> None:
    store.set_setting(REL, "address", "she/her, a woman", NOW - timedelta(days=1))
    talker = await _say(store, Judge(), "off", "made pasta")
    lines = talker.seen[0].card.split("\n")
    assert lines[1].startswith("[How they want to be referred to: she/her, a woman.")
