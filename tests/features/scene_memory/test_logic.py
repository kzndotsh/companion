from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.types import (
    Belief,
    BeliefId,
    Frame,
    Json,
    Provenance,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.scene_memory.logic import (
    BASICS_NOTE,
    KNOWN_NOTE,
    LIMITS_NOTE,
    OFFER_NOTE,
    BrushRead,
    Entry,
    Everyday,
    Excluded,
    Facts,
    Intimate,
    Offered,
    Pattern,
    Proposed,
    Quote,
    Stance,
    Why,
    agree,
    closed,
    cooled,
    parse_lanes,
    pattern_entry,
    refuse,
    render_scene,
    scene_card,
    scenes,
    screen,
    touches_age,
)
from tests.conftest import REL, T0

A, B, C = BeliefId("a"), BeliefId("b"), BeliefId("c")
INTO = Intimate(Stance.INTO)


def test_a_memory_is_intimate_only_when_all_three_reads_give_the_same_lane_and_stance() -> None:
    reads = [
        {A: INTO, B: INTO, C: Everyday()},
        {A: INTO, B: Intimate(Stance.STYLE), C: Everyday()},
        {A: INTO, B: INTO, C: Everyday()},
    ]
    assert agree(reads, [A, B, C]) == {A: INTO, B: Excluded(Why.DOUBT), C: Everyday()}


def test_a_lane_split_or_a_memory_a_read_left_out_is_doubt() -> None:
    reads = [{A: INTO, B: INTO}, {A: Everyday(), B: INTO}, {A: INTO}]
    assert agree(reads, [A, B]) == {A: Excluded(Why.DOUBT), B: Excluded(Why.DOUBT)}


def test_an_intimate_read_with_no_stance_is_no_vote() -> None:
    refs = {"b1": A, "b2": B}
    data: Json = {
        "labels": [
            {"ref": "b1", "lane": "intimate", "stance": "none"},
            {"ref": "[b2]", "lane": "intimate", "stance": "curious"},
            {"ref": "b9", "lane": "everyday", "stance": "none"},
        ]
    }
    assert parse_lanes(data, refs) == {B: Intimate(Stance.CURIOUS)}
    assert parse_lanes({"oops": 1}, refs) is None


@pytest.mark.parametrize(
    "text",
    [
        "likes roleplay where she is 16",
        "plays a 15-year-old",
        "she is 9.",
        "enjoys a little space headspace",
        "likes being called a little one",
        "wants a schoolgirl scene",
        "likes teacher and student play",
        "is into ageplay",
        "wants to feel young again in bed",
        "likes ddlg",
    ],
)
def test_the_age_check_catches_age_minors_school_and_the_headspace(text: str) -> None:
    assert touches_age(text)


@pytest.mark.parametrize(
    "text",
    [
        "likes being tied up",
        "wants slow kissing first",
        "is into praise",
        "as of 2026-10-14 loves being kissed at 10:30 at night",
    ],
)
def test_the_age_check_lets_ordinary_adult_wording_through(text: str) -> None:
    assert not touches_age(text)


def _said(
    belief: Callable[..., Belief], claim: str, quote: str = "i like it slow", **kw: object
) -> Belief:
    return belief(bid="x", claim=claim, quote=quote, **kw)


def test_everyday_stays_everyday_whatever_it_mentions(belief: Callable[..., Belief]) -> None:
    b = _said(belief, "works at a school", quote="i teach at a school")
    assert screen(Everyday(), b, Facts(held=True, heavy=True)) == Everyday()


def test_the_floor_keeps_age_out_of_scenes_in_the_claim_or_the_quote(
    belief: Callable[..., Belief],
) -> None:
    by_claim = _said(belief, "likes schoolgirl outfits in bed")
    by_quote = _said(belief, "likes a costume", quote="the uniform from when i was 15")
    assert screen(INTO, by_claim, Facts()) == Excluded(Why.FLOOR)
    assert screen(INTO, by_quote, Facts()) == Excluded(Why.FLOOR)


def test_a_doubtful_memory_that_touches_age_is_the_floors(belief: Callable[..., Belief]) -> None:
    b = _said(belief, "likes being a little in scenes")
    assert screen(Excluded(Why.DOUBT), b, Facts()) == Excluded(Why.FLOOR)
    assert screen(Excluded(Why.DOUBT), _said(belief, "likes slow"), Facts()) == Excluded(Why.DOUBT)


def test_a_turn_the_minor_check_held_keeps_a_memory_out(belief: Callable[..., Belief]) -> None:
    assert screen(INTO, _said(belief, "likes slow"), Facts(held=True)) == Excluded(Why.FLOOR)


def test_crisis_level_and_heavy_sharing_keep_a_memory_out(belief: Callable[..., Belief]) -> None:
    crisis = _said(belief, "likes slow", sensitivity=3)
    assert screen(INTO, crisis, Facts()) == Excluded(Why.CRISIS)
    assert screen(INTO, _said(belief, "likes slow"), Facts(heavy=True)) == Excluded(Why.LISTENING)
    assert screen(INTO, _said(belief, "likes slow", sensitivity=2), Facts()) == INTO


def test_a_limit_comes_only_from_their_own_plain_words(belief: Callable[..., Belief]) -> None:
    hard = Intimate(Stance.HARD_LIMIT)
    stated = _said(belief, "never wants choking", quote="no choking ever")
    inferred = _said(belief, "never wants choking", provenance=Provenance.INFERRED)
    played = _said(belief, "never wants choking", frame=Frame.PLAY, provenance=Provenance.PLAYED)
    assert screen(hard, stated, Facts()) == hard
    assert screen(hard, inferred, Facts()) == Excluded(Why.NOT_THEIR_WORDS)
    assert screen(hard, played, Facts()) == Excluded(Why.NOT_THEIR_WORDS)
    assert screen(INTO, inferred, Facts()) == INTO


def _u(n: int, speaker: Speaker, frame: Frame, minutes: int, text: str = "") -> Utterance:
    return Utterance(
        UtteranceId(f"u{n}"),
        REL,
        SessionId("s"),
        TurnId(f"t{n}"),
        speaker,
        text or f"message {n}",
        frame,
        "test",
        T0 + timedelta(minutes=minutes),
    )


def test_scenes_are_cut_by_a_message_out_of_play_and_by_a_long_gap() -> None:
    play, real = Frame.PLAY, Frame.REAL
    msgs = [
        _u(1, Speaker.USER, real, 0),
        _u(2, Speaker.USER, play, 1),
        _u(3, Speaker.COMPANION, play, 2),
        _u(4, Speaker.USER, play, 3),
        _u(5, Speaker.USER, real, 4),
        _u(6, Speaker.COMPANION, real, 5),
        _u(7, Speaker.USER, play, 6),
        _u(8, Speaker.USER, play, 6 + 180),
    ]
    found = scenes(msgs)
    assert [[u.id for u in s.messages] for s in found] == [["u2", "u3", "u4"], ["u7"], ["u8"]]
    assert closed(found[0], msgs, T0 + timedelta(minutes=10))
    assert not closed(found[2], msgs, T0 + timedelta(minutes=190))
    assert closed(found[2], msgs, T0 + timedelta(minutes=186 + 120))


def _labels() -> dict[str, Utterance]:
    theirs = _u(1, Speaker.USER, Frame.PLAY, 0, "*pulls you closer* slower this time")
    return {"m1": theirs, "m2": _u(2, Speaker.COMPANION, Frame.PLAY, 1, "slower this time")}


def _proposed(**kw: str) -> Proposed:
    base = {
        "pattern": "",
        "claim": "In scenes, the user tends to ask for a slow pace.",
        "stance": "style",
        "message": "m1",
        "quote": "slower this time",
    }
    return Proposed(**(base | kw))


def test_a_pattern_is_their_own_play_quoted_exactly_and_never_a_limit() -> None:
    labels = _labels()
    assert refuse(_proposed(), labels) is None
    assert refuse(_proposed(stance="hard_limit"), labels) == "a pattern is never a limit"
    assert refuse(_proposed(quote="faster"), labels) == "the quote is not in their message"
    assert refuse(_proposed(message="m2"), labels) == "not one of their own messages in the scene"
    assert refuse(_proposed(claim="In scenes, the user tends to play a teen."), labels) == (
        "excluded by the floor"
    )


def _pattern(*scene_keys: str, retired: bool = False) -> Pattern:
    quotes = tuple(Quote(UtteranceId(k), UtteranceId(f"{k}-said"), "slower") for k in scene_keys)
    return Pattern("p", "In scenes, the user tends to go slow.", Stance.STYLE, quotes, retired)


def test_a_pattern_is_an_entry_only_once_seen_in_two_separate_scenes() -> None:
    assert pattern_entry(_pattern("s1")) is None
    assert pattern_entry(_pattern("s1", "s1")) is None  # two quotes from one scene
    entry = pattern_entry(_pattern("s1", "s2"))
    assert entry is not None
    assert entry.scenes == 2
    assert pattern_entry(_pattern("s1", "s2", retired=True)) is None
    assert pattern_entry(_pattern("s1", "s2"), held={UtteranceId("s2-said")}) is None


def _entry(eid: str, stance: Stance) -> Entry:
    return Entry(eid, f"claim {eid}", stance, ("q",))


ENTRIES = [
    _entry("into1", Stance.INTO),
    _entry("soft", Stance.SOFT_LIMIT),
    _entry("style", Stance.STYLE),
    _entry("hard", Stance.HARD_LIMIT),
    _entry("care", Stance.AFTERCARE),
    _entry("into2", Stance.INTO),
    _entry("cur1", Stance.CURIOUS),
    _entry("cur2", Stance.CURIOUS),
]
SCORES = {"into1": 0.2, "style": 0.9, "care": 0.5, "into2": 0.7, "cur1": 0.95, "cur2": 0.6}


def test_the_scene_card_pins_limits_then_the_nearest_then_one_offer_then_the_basics() -> None:
    card = scene_card(ENTRIES, SCORES, ["The user's name is Sam."], may_offer=True)
    assert [e.id for e in card.limits] == ["hard", "soft"]
    assert [e.id for e, _ in card.nearest] == ["style", "into2", "care"]
    assert card.offer is not None
    assert card.offer.id == "cur1"
    text = render_scene(card)
    heads = [n.text.split("\n")[0] for n in (LIMITS_NOTE, KNOWN_NOTE, OFFER_NOTE, BASICS_NOTE)]
    at = [text.index(h) for h in heads]
    assert at == sorted(at)
    assert text.index("hard limit: claim hard") < text.index("soft limit: claim soft")
    assert "claim cur1" in text
    assert "claim cur2" not in text
    assert "claim into1" not in text


def test_a_limit_is_pinned_even_with_no_look_up_and_nothing_else_is_shown() -> None:
    card = scene_card(ENTRIES, {}, [], may_offer=True)
    assert [e.id for e in card.limits] == ["hard", "soft"]
    assert card.nearest == ()
    assert card.offer is None


def test_no_offer_unless_it_may_and_never_one_that_was_pushed_back() -> None:
    assert scene_card(ENTRIES, SCORES, [], may_offer=False).offer is None
    cooled_one = scene_card(ENTRIES, SCORES, [], may_offer=True, cooled={"cur1"})
    assert cooled_one.offer is not None
    assert cooled_one.offer.id == "cur2"


def test_a_curious_pattern_read_from_how_they_played_is_never_offered() -> None:
    played = Entry(
        "pat", "In scenes, the user tends to ask for more", Stance.CURIOUS, ("q",), scenes=3
    )
    card = scene_card((played,), {"pat": 0.9}, [], may_offer=True)
    assert card.offer is None


def test_an_item_cools_when_the_next_brush_off_read_after_its_offer_declined() -> None:
    now = T0 + timedelta(days=1)
    at = [T0 + timedelta(minutes=m) for m in range(5)]
    offers = [
        Offered(at[0], TurnId("t1"), "cur1"),
        Offered(at[2], TurnId("t3"), "cur2"),
        Offered(now - timedelta(days=4), TurnId("t0"), "cur3"),
    ]
    reads = [
        BrushRead(at[0], TurnId("t1"), declined=False),  # the offer's own turn does not count
        BrushRead(at[1], TurnId("t2"), declined=True),
        BrushRead(at[3], TurnId("t4"), declined=False),
        BrushRead(at[4], TurnId("t5"), declined=True),  # not the next read after cur2's offer
        BrushRead(now - timedelta(days=4, minutes=-1), TurnId("x"), declined=True),
    ]
    assert cooled(offers, reads, now) == {"cur1"}
