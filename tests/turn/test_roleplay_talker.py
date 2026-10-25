from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import FALLBACK, Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
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
from companion.features.basics.logic import name_belief
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

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
    """Says every message that needs a frame is play, reads every turn as ordinary and not
    age-coded unless told otherwise, and gives the other judges an inert answer."""

    def __init__(
        self,
        *,
        age_coded: bool | None = False,
        intimate: bool = False,
        sexual_reply: bool = False,
        explicit: bool = True,
        declines: bool = False,
    ) -> None:
        self.age_coded, self.intimate, self.sexual_reply = age_coded, intimate, sexual_reply
        self.explicit, self.declines = explicit, declines

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del user
        if "label the frame" in system:
            return Extraction({"frame": "play", "confidence": 0.95}, "j", 0.0, 1)
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"intimate"}:
            return Extraction({"intimate": self.sexual_reply}, "j", 0.0, 1)
        if isinstance(props, dict) and set(props) == {"explicit"}:
            return Extraction({"explicit": self.explicit}, "j", 0.0, 1)
        if isinstance(props, dict) and set(props) == {"declines"}:
            return Extraction({"declines": self.declines}, "j", 0.0, 1)
        if isinstance(props, dict) and "age_coded" in props and self.age_coded is not None:
            labels: Json = {
                "severity": 0,
                "stance": "other",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": False,
                "topic": "",
                "intimate": self.intimate,
                "age_coded": self.age_coded,
            }
            return Extraction(labels, "j", 0.0, 1)
        return Extraction(None, "j", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _chat(
    store: Store, texts: list[str], scene: Talker | None, judge: Judge | None = None
) -> Talker:
    everyday = Talker("everyday")
    convo = Conversation(
        store, everyday, PREFIX, REL, judge=judge or Judge(), roleplay_talker=scene
    )
    for i, text in enumerate(texts):
        await handle(convo, SESSION, text, "t", NOW + timedelta(minutes=i))
    return everyday


async def test_the_roleplay_talker_takes_over_once_a_scene_is_in_progress(store: Store) -> None:
    scene = Talker("scene")
    everyday = await _chat(
        store, ["let's pretend you're a knight", "*bows*", "and then what"], scene
    )
    assert len(everyday.seen) == 1  # the message that started the scene
    assert len(scene.seen) == 2


async def test_without_a_roleplay_talker_everyone_is_answered_by_the_everyday_one(
    store: Store,
) -> None:
    everyday = await _chat(store, ["let's pretend you're a knight", "*bows*", "and then?"], None)
    assert len(everyday.seen) == 3


async def test_ordinary_chat_never_reaches_the_roleplay_talker(store: Store) -> None:
    scene = Talker("scene")
    everyday = await _chat(store, ["i got a haircut", "it looks okay", "thanks"], scene)
    assert len(everyday.seen) == 3
    assert scene.seen == []


async def test_the_choice_is_logged_with_a_reason_written_by_code(store: Store) -> None:
    await _chat(store, ["let's pretend you're a knight", "*bows*"], Talker("scene"))
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [d.reason for d in store.decisions_for_turn(REL, turn)]
    assert "replied with the roleplay talker: a pretend scene is in progress" in reasons


@pytest.mark.parametrize(
    ("age_coded", "reason"),
    [
        (True, "floor: kept on the everyday talker, the judge read age-coded content"),
        (None, "kept on the everyday talker: the judge could not read the turn"),
    ],
)
async def test_a_scene_stays_with_the_everyday_talker_when_the_floor_holds_or_it_was_not_read(
    store: Store, age_coded: bool | None, reason: str
) -> None:
    scene = Talker("scene")
    everyday = await _chat(
        store, ["let's pretend you're a knight", "*bows*"], scene, Judge(age_coded=age_coded)
    )
    assert scene.seen == []
    assert len(everyday.seen) == 2
    turn = store.latest_turn(REL)
    assert turn is not None
    assert reason in [d.reason for d in store.decisions_for_turn(REL, turn)]


@pytest.mark.parametrize(
    ("allowed", "age_coded", "routed"),
    [(True, False, True), (False, False, False), (True, True, False)],
)
async def test_intimate_talk_goes_to_the_roleplay_talker_only_when_allowed_and_above_the_floor(
    store: Store, *, allowed: bool, age_coded: bool, routed: bool
) -> None:
    scene, everyday = Talker("scene"), Talker("everyday")
    convo = Conversation(
        store,
        everyday,
        PREFIX,
        REL,
        judge=Judge(intimate=True, age_coded=age_coded),
        roleplay_talker=scene,
        route_intimate=allowed,
    )
    await handle(convo, SESSION, "i want you so bad", "t", NOW)
    assert (len(scene.seen), len(everyday.seen)) == ((1, 0) if routed else (0, 1))


@pytest.mark.parametrize(("sexual", "sent"), [(False, "everyday"), (True, None)])
async def test_a_held_turn_gets_the_note_and_an_intimate_reply_three_times_sends_nothing(
    store: Store, *, sexual: bool, sent: str | None
) -> None:
    scene, everyday = Talker("scene"), Talker("everyday")
    convo = Conversation(
        store,
        everyday,
        PREFIX,
        REL,
        judge=Judge(intimate=True, age_coded=True, sexual_reply=sexual),
        roleplay_talker=scene,
        route_intimate=True,
    )
    out = await handle(convo, SESSION, "i want you so bad", "t", NOW)
    assert scene.seen == []
    assert "keep this reply free of anything sexual" in everyday.seen[0].card
    if sent is None:
        assert out == ""  # nothing is sent: no reply is written by code
        assert len(everyday.seen) == 3
        assert len(everyday.seen[2].messages) == 1  # the last draw sees only their message
    else:
        assert len(everyday.seen) == 1


async def test_a_scene_reply_with_an_em_dash_is_drawn_once_more(store: Store) -> None:
    class Dashing:
        def __init__(self) -> None:
            self.seen: list[TalkerRequest] = []

        async def reply(self, request: TalkerRequest) -> Reply:
            self.seen.append(request)
            text = "I lean in\u2014closer" if len(self.seen) == 1 else "I lean in, closer"
            return Reply(text=text, model="scene", latency_ms=1)

    scene, everyday = Dashing(), Talker("everyday")
    convo = Conversation(
        store, everyday, PREFIX, REL, judge=Judge(), roleplay_talker=scene, resample=True
    )
    await handle(convo, SESSION, "let's pretend you're a knight", "t", NOW)
    out = await handle(convo, SESSION, "*bows*", "t", NOW + timedelta(minutes=1))
    assert out == "I lean in, closer"
    assert len(scene.seen) == 2


async def test_a_scene_reading_from_the_fallback_model_never_routes(store: Store) -> None:
    class FallbackJudge(Judge):
        async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
            got = await super().extract(system, user, schema)
            return Extraction(got.data, got.model + FALLBACK, 0.0, 1)

    scene = Talker("scene")
    everyday = await _chat(
        store, ["let's pretend you're a knight", "*bows*"], scene, FallbackJudge()
    )
    assert scene.seen == []
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [d.reason for d in store.decisions_for_turn(REL, turn)]
    assert "kept on the everyday talker: the judge could not read the turn" in reasons
    assert (
        len(everyday.seen) == 4
    )  # its intimate checks are unread too, so the held reply is redrawn twice


class Forgot(Judge):
    """Reads the newest message as "you forgot" about their name, and picks the first memory."""

    def __init__(self, *, finds: bool) -> None:
        super().__init__()
        self.finds = finds

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and "age_coded" in props and "you forgot" in user:
            labels: Json = {
                "severity": 0,
                "stance": "other",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": True,
                "repair": False,
                "topic": "what to call them",
                "intimate": False,
                "age_coded": False,
            }
            return Extraction(labels, "j", 0.0, 1)
        if isinstance(props, dict) and set(props) == {"labels"}:
            return Extraction({"labels": ["r1"] if self.finds else []}, "j", 0.0, 1)
        return await super().extract(system, user, schema)


def _named(store: Store) -> None:
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "robin",
        Frame.REAL,
        "t",
        NOW - timedelta(days=1),
    )
    store.append_utterance(said)
    store.insert_belief(name_belief(said, "Robin", "b1", said.at))


@pytest.mark.parametrize("finds", [True, False])
async def test_you_forgot_in_a_scene_looks_it_up_and_an_empty_look_up_adds_nothing(
    store: Store, *, finds: bool
) -> None:
    _named(store)
    scene = Talker("scene")
    texts = ["let's pretend you're a knight", "*bows*", "you forgot.. again :("]
    await _chat(store, texts, scene, Forgot(finds=finds))
    card = scene.seen[-1].card
    assert ("They asked you to remember this" in card) is finds
    assert "holds nothing on it" not in card


async def test_flirting_stays_with_the_everyday_talker_until_a_message_is_explicit(
    store: Store,
) -> None:
    everyday, scene = Talker("everyday"), Talker("scene")
    convo = Conversation(
        store,
        everyday,
        PREFIX,
        REL,
        judge=Judge(intimate=True, explicit=False),
        roleplay_talker=scene,
        route_intimate=True,
    )
    await handle(convo, SESSION, "you look cute today", "test", NOW)
    assert (len(everyday.seen), len(scene.seen)) == (1, 0)
    assert "keep this reply free" not in everyday.seen[0].card  # not held: no floor note
    await handle(convo, SESSION, "come closer then", "test", NOW + timedelta(minutes=1))
    assert (len(everyday.seen), len(scene.seen)) == (2, 0)  # a run of flirting is not under way
    convo.judge.explicit = True  # type: ignore[union-attr]
    await handle(convo, SESSION, "take it off", "test", NOW + timedelta(minutes=2))
    assert (len(everyday.seen), len(scene.seen)) == (2, 1)
    convo.judge.explicit = False  # type: ignore[union-attr]
    await handle(convo, SESSION, "mm yes", "test", NOW + timedelta(minutes=3))
    assert (len(everyday.seen), len(scene.seen)) == (2, 2)  # under way: it carries on


async def test_a_push_back_in_a_scene_is_answered_by_the_everyday_talker_with_a_note(
    store: Store,
) -> None:
    from companion.core.turn.floor import BRUSH_NOTE  # noqa: PLC0415

    everyday, scene = Talker("everyday"), Talker("scene")
    playing = Conversation(store, everyday, PREFIX, REL, judge=Judge(), roleplay_talker=scene)
    await handle(playing, SESSION, "*waves at you from across the room*", "test", NOW)
    await handle(playing, SESSION, "*sits down next to you*", "test", NOW + timedelta(minutes=1))
    assert len(scene.seen) == 1  # the scene is under way
    pushed = Conversation(
        store, everyday, PREFIX, REL, judge=Judge(declines=True), roleplay_talker=scene
    )
    await handle(pushed, SESSION, "*bonk* behave, i'm starving", "test", NOW + timedelta(minutes=2))
    assert len(scene.seen) == 1
    assert BRUSH_NOTE.text.strip("[]") in everyday.seen[-1].card
    assert "keep this reply free" not in everyday.seen[-1].card  # no floor hold


def test_a_route_is_read_from_its_detail_and_an_old_one_by_its_reason() -> None:
    from companion.core.types import (  # noqa: PLC0415
        Decision,
        DecisionId,
        DecisionKind,
        TraceId,
        TurnId,
    )
    from companion.turn.route import routed_to_roleplay  # noqa: PLC0415

    def route(reason: str, detail: dict[str, Json] | None) -> Decision:
        return Decision(
            DecisionId("d"),
            REL,
            SESSION,
            TurnId("t"),
            TraceId("t"),
            DecisionKind.POLICY,
            reason,
            NOW,
            detail=detail,
            key="route",
        )

    assert routed_to_roleplay(route("anything", {"talker": "roleplay"}))
    assert not routed_to_roleplay(
        route("replied with the roleplay talker: x", {"talker": "everyday"})
    )
    assert routed_to_roleplay(route("replied with the roleplay talker: a scene", None))
    assert not routed_to_roleplay(route("floor: kept on the everyday talker", None))


async def test_a_failing_shadow_look_up_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    import asyncio  # noqa: PLC0415

    from companion.turn.beside import beside  # noqa: PLC0415

    async def boom() -> None:
        raise RuntimeError("embedder down")

    beside(boom())
    await asyncio.sleep(0.05)
    assert "shadow look-up failed" in caplog.text
