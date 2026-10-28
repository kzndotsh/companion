from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion import prompts
from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    RelationshipId,
    SessionId,
    Speaker,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.mood.logic import Source, State, effect
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
SESSION = SessionId("s")
NOW = datetime(2026, 10, 19, 17, 0, tzinfo=UTC)
PREFIX = build_prefix("You are a companion. " * 300)
# notes reach the model inside <notes>, without their brackets (core/prompt/sections.py)
PLAYFUL = prompts.get("notes/mood-playful").text.strip("[]")
TENDER = prompts.get("notes/mood-tender").text.strip("[]")


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
        elif set(props) == {"name"}:
            data = {"name": "Robin"}
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
    await handle(
        Runtime(store, talker, PREFIX, REL, judge=judge, mood=mode), SESSION, text, "test", at
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
    runtime = Runtime(store, Talker(fail=True), PREFIX, REL, judge=Judge(), mood="on")
    with pytest.raises(RuntimeError):
        await handle(runtime, SESSION, "haha yesss!! 😂", "test", NOW)
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
    notes = talker.seen[0].card.split("<notes>\n", 1)[1]
    assert notes.startswith("How they want to be referred to: she/her, a woman.")  # the first note


@pytest.mark.parametrize(("severity", "shown"), [(0, False), (1, True)])
async def test_held_memories_are_in_view_only_when_they_are_sharing_something(
    store: Store, severity: int, *, shown: bool
) -> None:
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "i slip up sometimes",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    store.append_utterance(said)
    store.insert_belief(
        Belief(
            id=BeliefId("b1"),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.TRAIT,
            claim="The user sometimes slips up.",
            evidence=(Evidence(said.id, "i slip up sometimes"),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.7,
            valid_from=said.at,
            recorded_at=said.at,
            sensitivity=2,
        )
    )
    talker = await _say(store, Judge(severity=severity), "off", "i want a beer lol")
    assert ("The user sometimes slips up." in talker.seen[0].card) is shown


async def test_what_to_call_them_is_asked_once_a_day_on_a_casual_turn(store: Store) -> None:
    first = await _say(store, Judge(), "off", "made pasta")
    later = await _say(store, Judge(), "off", "it was good", NOW + timedelta(hours=2))
    next_day = await _say(store, Judge(), "off", "morning", NOW + timedelta(hours=25))
    asks = [t.seen[0].card.count("You do not know their name") for t in (first, later, next_day)]
    assert asks == [1, 0, 1]


async def test_their_answer_to_what_to_call_them_is_remembered_in_their_words(store: Store) -> None:
    asked = Utterance(
        UtteranceId("c0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.COMPANION,
        "what name do you like being called?",
        Frame.REAL,
        "test",
        NOW - timedelta(minutes=1),
    )
    store.append_utterance(asked)
    await _say(store, Judge(), "off", "Robin")
    [b] = [b for b in store.user_beliefs(REL) if "name" in b.claim]
    assert b.claim == "The user's name is Robin."
    assert b.evidence[0].quote == "Robin"
    later = await _say(store, Judge(), "off", "made pasta", NOW + timedelta(days=2))
    assert "You do not know their name" not in later.seen[0].card
