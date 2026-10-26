"""The scene memory on a turn (ADR 0026): what the request carries on a scene turn and on an
everyday one, in each mode."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from companion.core.turn.floor import BRUSH_KEY
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    Speaker,
    Subject,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.relevance.logic import LIVE
from companion.features.scene_memory.logic import (
    BASICS_NOTE,
    KNOWN_NOTE,
    LIMITS_NOTE,
    OFFER_NOTE,
    Everyday,
    Intimate,
    Place,
    Stance,
)
from companion.features.scene_memory.run import CARD, LEFT_OFF, OFFERED, Scored, entries
from companion.features.scene_memory.store import By
from companion.loops.conversation import Conversation
from companion.loops.current import Turn
from companion.loops.features import Lookups
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store
from companion.turn.assemble import Assembled, assemble
from companion.turn.fast import handle
from tests.features.relevance.test_run import Embedder, Picker
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

NAME = "The user's name is Sam."
NURSE = "The user works nights as a nurse."
SLOW = "The user loves slow kissing."
CHOKE = "The user never wants choking."
TEASE = "The user is unsure about being teased hard."
BLIND = "The user wants to try blindfolds."
PLACES: dict[str, Place] = {
    NAME: Everyday(),
    NURSE: Everyday(),
    SLOW: Intimate(Stance.INTO),
    CHOKE: Intimate(Stance.HARD_LIMIT),
    TEASE: Intimate(Stance.SOFT_LIMIT),
    BLIND: Intimate(Stance.CURIOUS),
}


def _heads() -> list[str]:
    return [n.text.split("\n")[0] for n in (LIMITS_NOTE, KNOWN_NOTE, OFFER_NOTE, BASICS_NOTE)]


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    for n, (claim, _) in enumerate(PLACES.items()):
        said = Utterance(
            UtteranceId(f"u{n}"),
            REL,
            SESSION,
            TurnId(f"t{n}"),
            Speaker.USER,
            claim,
            Frame.REAL,
            "test",
            NOW - timedelta(days=1, minutes=-n),
        )
        s.append_utterance(said)
        s.insert_belief(
            Belief(
                id=BeliefId(f"b{n}"),
                relationship_id=REL,
                subject=Subject.USER,
                kind=BeliefKind.PREFERENCE,
                claim=claim,
                evidence=(Evidence(said.id, claim),),
                provenance=Provenance.STATED,
                speaker=Speaker.USER,
                frame=Frame.REAL,
                confidence=0.8,
                valid_from=said.at,
                recorded_at=said.at,
            )
        )
    by_claim = {b.claim: b.id for b in s.user_beliefs(REL)}
    by = By("fake", "system/scene-lane@v1", NOW - timedelta(hours=1))
    s.scene_memory().place({by_claim[c]: p for c, p in PLACES.items()}, by)
    return s


TURN = TurnId("t-now")


def _convo(store: Store, mode: str) -> Conversation:
    return Conversation(store, Talker(), PREFIX, REL, roleplay_talker=Talker(), scene_memory=mode)


def _brush(store: Store, *, declines: bool | None, turn: TurnId = TURN, at: datetime = NOW) -> None:
    detail: dict[str, Json] = {"declines": bool(declines)}
    if declines is not None:
        detail["scorer"] = "fake"
    Recorder(store, REL, SESSION, turn, TraceId(turn), at).decide(BRUSH_KEY, detail)


def _scores(store: Store) -> Lookups:
    found = entries(store, REL)
    near = {SLOW: 0.9, BLIND: 0.8}
    return Lookups(found={"scene": Scored(found, {e.id: near.get(e.claim, 0.1) for e in found})})


def _turn(store: Store, mode: str, *, roleplay: bool, looked: Lookups | None = None) -> Assembled:
    t = Turn(SESSION, TURN, NOW, [], "*leans in*")
    in_scene = Frame.PLAY if roleplay else Frame.REAL
    return assemble(
        _convo(store, mode), t, in_scene, None, looked or _scores(store), roleplay=roleplay
    )


def _keys(store: Store, key: str) -> list[dict[str, Json]]:
    return [d.detail or {} for d in store.decisions_with_key(REL, key)]


def test_on_a_scene_turn_the_card_is_limits_nearest_offer_basics_and_nothing_everyday(
    store: Store,
) -> None:
    _brush(store, declines=False)
    asm = _turn(store, "on", roleplay=True)
    card = asm.request.card
    at = [card.index(h) for h in _heads()]
    assert at == sorted(at)
    assert card.index(CHOKE) < card.index(TEASE) < card.index(SLOW) < card.index(BLIND)
    assert card.index(BLIND) < card.index(NAME)
    assert NURSE not in card
    assert "[What you remember" not in card
    [logged] = _keys(store, CARD)
    assert logged["sent"] is True
    assert logged["offer"] is not None
    for write in asm.after:
        write()
    assert [d["entry"] for d in _keys(store, OFFERED)] == [logged["offer"]]


def test_in_shadow_a_scene_turn_logs_the_scene_card_and_sends_todays(store: Store) -> None:
    _brush(store, declines=False)
    today = _turn(store, "off", roleplay=True).request.card
    shadow = _turn(store, "shadow", roleplay=True)
    assert shadow.request.card == today
    assert SLOW in today
    assert NURSE in today
    [logged] = _keys(store, CARD)
    assert logged["sent"] is False
    assert BLIND in str(logged["text"])
    for write in shadow.after:
        write()
    assert _keys(store, OFFERED) == []


def test_on_an_everyday_turn_never_shows_the_intimate_lane(store: Store) -> None:
    card = _turn(store, "on", roleplay=False).request.card
    assert NURSE in card
    assert NAME in card
    for claim in (SLOW, CHOKE, TEASE, BLIND):
        assert claim not in card
    [logged] = _keys(store, LEFT_OFF)
    assert len(logged["beliefs"]) == 4  # type: ignore[arg-type]
    assert logged["sent"] is False


def test_in_shadow_an_everyday_turn_logs_what_it_would_leave_off_and_sends_it(
    store: Store,
) -> None:
    card = _turn(store, "shadow", roleplay=False).request.card
    assert SLOW in card
    [logged] = _keys(store, LEFT_OFF)
    assert logged["sent"] is True


def test_switch_off_logs_nothing_and_changes_nothing(store: Store) -> None:
    _brush(store, declines=False)
    _turn(store, "off", roleplay=True)
    _turn(store, "off", roleplay=False)
    assert _keys(store, CARD) == []
    assert _keys(store, LEFT_OFF) == []


def test_no_offer_unless_this_turns_brush_off_read_answered_no(store: Store) -> None:
    _brush(store, declines=None)  # the read failed: no is not known
    card = _turn(store, "on", roleplay=True).request.card
    assert BLIND not in card
    assert SLOW in card


def test_an_item_they_pushed_back_is_not_offered_again_within_three_days(store: Store) -> None:
    blind = next(e.id for e in entries(store, REL) if e.claim == BLIND)
    earlier = TurnId("t-earlier")
    Recorder(store, REL, SESSION, earlier, TraceId("e"), NOW - timedelta(days=1)).decide(
        OFFERED, {"entry": blind}
    )
    _brush(store, declines=True, turn=TurnId("t-next"), at=NOW - timedelta(days=1, minutes=-1))
    _brush(store, declines=False)
    assert BLIND not in _turn(store, "on", roleplay=True).request.card


def test_with_no_look_up_a_scene_keeps_its_limits_and_basics(store: Store) -> None:
    _brush(store, declines=False)
    card = _turn(store, "on", roleplay=True, looked=Lookups()).request.card
    assert CHOKE in card
    assert NAME in card
    assert SLOW not in card
    assert BLIND not in card


async def test_on_the_relevance_look_up_never_searches_the_intimate_lane(store: Store) -> None:
    talker = Talker()
    convo = Conversation(
        store,
        talker,
        PREFIX,
        REL,
        judge=Picker(),
        embedder=Embedder(),
        embed_model="fake-embed",
        relevance="on",
        scene_memory="on",
    )
    await handle(convo, SESSION, "what a day", "test", NOW)
    [live] = [d.detail for d in store.decisions_with_key(REL, LIVE)]
    assert live is not None
    assert live["searched"] == 2  # the name and the work, none of the four intimate memories
