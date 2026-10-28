"""The crisis path in whole turns (ADR 0022): what changes when it is on, and that nothing changes
in shadow."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.crisis import HOLD_KEY, LINE, reach_held
from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.turn.ack import Reaction, ThenSend
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.crisis.logic import concern_note, light_note
from companion.features.crisis.run import LEVEL, LIGHT_KEY, LINE_SENT, METHOD, SCENE
from companion.kit.runtime import Runtime
from companion.prompts import get
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
CONCERN: Json = {
    "kind": "suicidal_thoughts",
    "literal": True,
    "timing": "hypothetical",
    "plan_or_means": False,
}
URGENT: Json = {"kind": "substance_taken", "literal": True, "timing": "now", "plan_or_means": True}
JOKE: Json = {
    "kind": "suicidal_thoughts",
    "literal": False,
    "timing": "hypothetical",
    "plan_or_means": False,
}
PLAIN: Json = {"kind": "none", "literal": True, "timing": "hypothetical", "plan_or_means": False}
DEFAULT_LINE = get("messages/crisis-line").render(line=LINE)


class Talker:
    def __init__(self, name: str = "everyday", replies: Sequence[str] = ()) -> None:
        self.name, self.replies = name, list(replies)
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        text = self.replies.pop(0) if self.replies else f"{self.name} here"
        return Reply(text=text, model=self.name, latency_ms=1)


class Judge:
    """Reads every message at one severity, answers the risk judge from `risks` in turn (None
    is a failed read), and gives the other judges nothing usable."""

    def __init__(
        self, risks: Sequence[Json | None], severity: int = 0, *, ack: bool = False
    ) -> None:
        self.risks, self.severity, self.ack = list(risks), severity, ack
        self.risk_calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        props = schema["properties"]
        assert isinstance(props, dict)
        if "plan_or_means" in props:
            answer = self.risks[self.risk_calls % len(self.risks)]
            self.risk_calls += 1
            if answer is None:
                msg = "judge down"
                raise RuntimeError(msg)
            return Extraction(answer, "j", 0.0, 1)
        if self.ack and set(props) == {"kind", "confidence", "emoji"}:
            return Extraction({"kind": "ack", "confidence": 0.99, "emoji": "👍"}, "j", 0.0, 1)
        if "severity" in props:
            labels: Json = {
                "severity": self.severity,
                "stance": "listening",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": False,
                "topic": "",
                "intimate": False,
                "age_coded": False,
            }
            return Extraction(labels, "j", 0.0, 1)
        return Extraction(None, "j", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _runtime(
    store: Store,
    judge: Judge,
    mode: str,
    talker: Talker,
    *,
    roleplay_talker: Talker | None = None,
    serious_message: str = "",
) -> Runtime:
    return Runtime(
        store,
        talker,
        PREFIX,
        REL,
        judge=judge,
        crisis=mode,
        roleplay_talker=roleplay_talker,
        serious_message=serious_message,
    )


def _keys(store: Store) -> list[str]:
    turn = store.latest_turn(REL)
    assert turn is not None
    return [d.key or "" for d in store.decisions_for_turn(REL, turn)]


def _level(store: Store) -> dict[str, Json]:
    turn = store.latest_turn(REL)
    assert turn is not None
    found = [d for d in store.decisions_for_turn(REL, turn) if d.has_key(LEVEL)]
    assert len(found) == 1
    assert isinstance(found[0].detail, dict)
    return found[0].detail


def _held(store: Store, at: datetime) -> bool:
    return reach_held(lambda key, since: store.decided_since(REL, key, since), at)


async def test_in_shadow_it_reads_and_logs_but_nothing_changes(store: Store) -> None:
    talker = Talker()
    judge = Judge([URGENT])
    out = await handle(
        _runtime(store, judge, "shadow", talker), SESSION, "i took too many pills", "t", NOW
    )
    assert judge.risk_calls == 3
    detail = _level(store)
    assert detail["level"] == "urgent"
    would = detail["would"]
    assert isinstance(would, list)
    assert "send the crisis line after the reply" in would
    assert isinstance(out, str)  # no message of code's own
    assert concern_note() not in talker.seen[0].tail
    assert HOLD_KEY not in _keys(store)
    assert not _held(store, NOW + timedelta(hours=1))


async def test_with_no_cue_the_risk_judge_is_not_asked(store: Store) -> None:
    judge = Judge([URGENT], severity=1)
    await handle(_runtime(store, judge, "on", Talker()), SESSION, "work was annoying", "t", NOW)
    assert judge.risk_calls == 0
    assert _level(store)["level"] == "none"


async def test_a_serious_listening_read_asks_the_risk_judge(store: Store) -> None:
    judge = Judge([CONCERN], severity=2)
    await handle(_runtime(store, judge, "on", Talker()), SESSION, "everything is a lot", "t", NOW)
    assert judge.risk_calls == 3
    assert _level(store)["level"] == "concern"


async def test_on_a_concern_turn_the_note_goes_after_the_history_with_no_cap(store: Store) -> None:
    talker = Talker()
    out = await handle(
        _runtime(store, Judge([CONCERN]), "on", talker), SESSION, "i want to die honestly", "t", NOW
    )
    request = talker.seen[0]
    assert concern_note() in request.tail
    assert concern_note().strip("[]") not in request.card
    assert "under about" not in request.card  # no length cap
    assert isinstance(out, str)
    assert HOLD_KEY in _keys(store)
    assert _held(store, NOW + timedelta(hours=23))
    assert not _held(store, NOW + timedelta(hours=25))


async def test_on_an_urgent_turn_the_fixed_line_is_sent_once_after_the_reply(store: Store) -> None:
    talker = Talker(replies=["i'm here. are you safe?"])
    runtime = _runtime(store, Judge([URGENT]), "on", talker)
    out = await handle(runtime, SESSION, "i took way too many pills", "t", NOW)
    assert isinstance(out, ThenSend)
    assert out.reply == "i'm here. are you safe?"
    assert out.then == DEFAULT_LINE
    assert concern_note() in talker.seen[0].tail
    history = store.history_before(REL, NOW + timedelta(minutes=1), 10)
    assert [(u.speaker, u.text) for u in history][-2:] == [
        (Speaker.COMPANION, "i'm here. are you safe?"),
        (Speaker.COMPANION, DEFAULT_LINE),
    ]
    assert LINE_SENT in _keys(store)
    again = await handle(runtime, SESSION, "i took more pills", "t", NOW + timedelta(minutes=5))
    assert isinstance(again, str)  # not sent twice within the hour


async def test_the_fixed_line_comes_from_the_sheet_section_when_there_is_one(store: Store) -> None:
    runtime = _runtime(
        store,
        Judge([URGENT]),
        "on",
        Talker(),
        serious_message="hey. stay with me and reach $line right now, okay?",
    )
    out = await handle(runtime, SESSION, "i took too much of my meds", "t", NOW)
    assert isinstance(out, ThenSend)
    assert out.then == f"hey. stay with me and reach {LINE} right now, okay?"


async def test_a_unanimous_figurative_read_stands_down(store: Store) -> None:
    talker = Talker()
    out = await handle(_runtime(store, Judge([JOKE]), "on", talker), SESSION, "kms lol", "t", NOW)
    assert _level(store)["level"] == "figurative"
    assert isinstance(out, str)
    assert talker.seen[0].tail == "" or "crisis" not in talker.seen[0].tail
    assert concern_note() not in talker.seen[0].tail
    assert light_note() not in talker.seen[0].tail


async def test_a_failed_read_fails_safe(store: Store) -> None:
    talker = Talker()
    judge = Judge([JOKE, JOKE, None])
    await handle(_runtime(store, judge, "on", talker), SESSION, "kms", "t", NOW)
    assert _level(store)["level"] == "concern"
    assert concern_note() in talker.seen[0].tail


async def test_a_split_joke_gets_one_light_check_a_day(store: Store) -> None:
    talker = Talker()
    runtime = _runtime(store, Judge([JOKE, JOKE, PLAIN]), "on", talker)
    await handle(runtime, SESSION, "i'm dead", "t", NOW)
    assert light_note() in talker.seen[0].tail
    assert LIGHT_KEY in _keys(store)
    await handle(runtime, SESSION, "dead again lol", "t", NOW + timedelta(hours=2))
    assert light_note() not in talker.seen[1].tail


def _seed_scene(store: Store) -> None:
    for i, text in enumerate(["*draws a sword*", "*charges the dragon*"]):
        at = NOW - timedelta(minutes=10 - i)
        store.append_utterance(
            Utterance(
                UtteranceId(f"u{i}"),
                REL,
                SESSION,
                TurnId(f"t{i}"),
                Speaker.USER,
                text,
                Frame.PLAY,
                "t",
                at,
            )
        )


@pytest.mark.parametrize("mode", ["on", "shadow"])
async def test_a_literal_risk_in_a_scene_goes_to_the_everyday_talker_when_on(
    store: Store, mode: str
) -> None:
    _seed_scene(store)
    everyday, scene = Talker(), Talker("scene")
    runtime = _runtime(store, Judge([CONCERN]), mode, everyday, roleplay_talker=scene)
    await handle(runtime, SESSION, "honestly i want to die, not the character, me", "t", NOW)
    if mode == "on":
        assert (len(everyday.seen), len(scene.seen)) == (1, 0)
        assert concern_note() in everyday.seen[0].tail
    else:
        assert (len(everyday.seen), len(scene.seen)) == (0, 1)
    assert SCENE in _keys(store)


@pytest.mark.parametrize("mode", ["on", "shadow"])
async def test_a_reply_naming_a_method_is_drawn_again_when_on(store: Store, mode: str) -> None:
    talker = Talker(replies=["a lethal dose is not something to test", "are you safe right now?"])
    out = await handle(
        _runtime(store, Judge([CONCERN]), mode, talker),
        SESSION,
        "how many pills would it take",
        "t",
        NOW,
    )
    assert METHOD in _keys(store)
    if mode == "on":
        assert out == "are you safe right now?"
        assert len(talker.seen) == 2
    else:
        assert out == "a lethal dose is not something to test"
        assert len(talker.seen) == 1


async def test_off_reads_nothing(store: Store) -> None:
    judge = Judge([URGENT])
    await handle(
        _runtime(store, judge, "off", Talker()), SESSION, "i took too many pills", "t", NOW
    )
    assert judge.risk_calls == 0
    assert LEVEL not in _keys(store)


@pytest.mark.parametrize("mode", ["on", "off"])
async def test_with_the_path_on_a_short_cue_message_is_never_answered_by_a_reaction_alone(
    store: Store, mode: str
) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId("c0"),
            REL,
            SESSION,
            TurnId("t0"),
            Speaker.COMPANION,
            "that's a lot to carry.",
            Frame.REAL,
            "t",
            NOW - timedelta(minutes=1),
        )
    )
    talker = Talker()
    runtime = _runtime(store, Judge([URGENT], ack=True), mode, talker)
    out = await handle(runtime, SESSION, "took all my pills", "t", NOW)
    if mode == "on":
        assert isinstance(out, ThenSend)
        assert len(talker.seen) == 1
    else:
        assert isinstance(out, Reaction)  # the ack judge would have answered it with an emoji
