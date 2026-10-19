from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from companion.core.openloops import (
    NOTE_DELAY,
    LoopKind,
    LoopState,
    Making,
    OpenLoop,
    RawLoop,
    RawResolution,
    follow_up_time,
    loop_labels,
    loop_note,
    parse,
    parse_resolved,
    pick_note,
    render_open_loops,
    to_loop,
    to_resolution,
)
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

REL = RelationshipId("rel")
MON = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)  # a Monday afternoon


def _at(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 10, day, hour, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("when", "scale", "expected"),
    [
        ("tomorrow", "days", _at(14)),
        ("today", "hours", _at(13)),
        ("tonight", "hours", _at(13)),
        ("later", "hours", _at(13)),
        ("right now", "hours", _at(13)),
        ("next week, after i know the result", "days", _at(20)),
        ("when the snow melts", "days", _at(15)),
        ("later this week", "days", _at(15)),
        ("later in the month", "days", _at(15)),
        ("friday", "days", _at(17)),
        ("monday", "days", _at(20)),
        ("this weekend", "days", _at(18)),
        ("next week", "days", _at(20)),
        ("", "hours", _at(13)),
        ("", "days", _at(15)),
        ("", "unknown", _at(15)),
        ("soon", "unknown", _at(15)),
        ("december 4th", "days", datetime(2026, 12, 5, 10, 0, tzinfo=UTC)),
        ("oct 14", "days", _at(15)),
        ("on jan 2", "days", datetime(2027, 1, 3, 10, 0, tzinfo=UTC)),
        ("feb 30", "days", _at(15)),
    ],
)
def test_the_follow_up_is_the_morning_after_it_happens_or_a_few_days_on(
    when: str, scale: str, expected: datetime
) -> None:
    assert follow_up_time(when, scale, MON, UTC) == expected


def _utt(text: str, speaker: Speaker = Speaker.USER, frame: Frame = Frame.REAL) -> Utterance:
    return Utterance(
        UtteranceId("u1"), REL, SessionId("s"), TurnId("t"), speaker, text, frame, "test", MON
    )


def _raw(**over: object) -> RawLoop:
    base: dict[str, object] = {
        "ref": "m1",
        "quote": "going to the vet tomorrow",
        "claim": "vet visit",
        "when": "tomorrow",
        "scale": "days",
        "sensitivity": 0,
    }
    base.update(over)
    return RawLoop(**base)  # type: ignore[arg-type]


def _make(raw: RawLoop, u: Utterance, now: datetime = MON) -> OpenLoop | str:
    made = Making(REL, now, UTC, lambda: "loop-1")
    return to_loop(raw, {"m1": u}, made)


def test_a_good_loop_keeps_the_exact_quote_and_gets_its_follow_up_time() -> None:
    loop = _make(_raw(), _utt("ok so i'm Going To The Vet tomorrow, wish me luck"))
    assert isinstance(loop, OpenLoop)
    assert loop.quote == "Going To The Vet tomorrow"
    assert loop.follow_up_at == _at(14)
    assert loop.source_utterance_id == "u1"


@pytest.mark.parametrize(
    ("raw", "text", "why"),
    [
        (_raw(scale="minutes"), "going to the vet tomorrow", "minute-scale"),
        (_raw(sensitivity=2), "going to the vet tomorrow", "sensitive"),
        (_raw(quote="never said this"), "going to the vet tomorrow", "quote"),
        (_raw(claim=""), "going to the vet tomorrow", "claim"),
        (_raw(certainty="maybe"), "going to the vet tomorrow", "not a firm plan (maybe)"),
        (_raw(certainty="wish"), "going to the vet tomorrow", "not a firm plan (wish)"),
        (_raw(about_companion=True), "going to the vet tomorrow", "about the companion"),
    ],
)
def test_loops_that_must_not_be_recorded_say_why(raw: RawLoop, text: str, why: str) -> None:
    result = _make(raw, _utt(text))
    assert isinstance(result, str)
    assert why in result


def test_only_something_they_said_for_real_counts() -> None:
    assert "for real" in str(_make(_raw(), _utt("going to the vet tomorrow", frame=Frame.PLAY)))
    assert "for real" in str(
        _make(_raw(), _utt("going to the vet tomorrow", speaker=Speaker.COMPANION))
    )


def test_a_follow_up_that_passed_days_ago_is_not_recorded() -> None:
    result = _make(_raw(), _utt("going to the vet tomorrow"), now=MON + timedelta(days=10))
    assert "passed" in str(result)


def test_a_garbled_label_is_rescued_by_the_one_message_that_holds_the_quote() -> None:
    made = Making(REL, MON, UTC, lambda: "x")
    assert isinstance(
        to_loop(_raw(ref="m9"), {"m1": _utt("going to the vet tomorrow")}, made), OpenLoop
    )


def test_parse_accepts_labelled_items_and_refuses_anything_malformed() -> None:
    good: Json = {
        "loops": [
            {
                "ref": "m1",
                "quote": "q",
                "claim": " a  b ",
                "when": " Friday ",
                "scale": "days",
                "sensitivity": 1,
                "certainty": "firm",
                "about_companion": False,
                "kind": "follow_up",
            }
        ]
    }
    parsed = parse(good)
    assert parsed is not None
    assert parsed[0].claim == "a b"
    assert parsed[0].when == "friday"
    assert parse({"loops": []}) == []
    assert parse({"loops": [{"ref": "m1"}]}) is None
    assert parse({"nothing": 1}) is None
    assert parse(None) is None
    flag: Json = {
        "ref": "r",
        "quote": "q",
        "claim": "c",
        "when": "",
        "scale": "days",
        "sensitivity": True,
    }
    assert parse({"loops": [flag]}) is None


def _loop_from(u: Utterance) -> OpenLoop:
    made = Making(REL, MON, UTC, lambda: "loop-1")
    loop = to_loop(_raw(), {"m1": u}, made)
    assert isinstance(loop, OpenLoop)
    return loop


def test_a_loop_is_closed_only_by_their_own_words_that_hold_the_quote() -> None:
    loop = _loop_from(_utt("going to the vet tomorrow"))
    labels = loop_labels([loop])
    said = _utt("the vet went fine, she is all good")
    done = to_resolution(RawResolution("L1", "m2", "the vet went fine"), labels, {"m2": said})
    assert done == (loop, "the vet went fine")
    raws = [
        (RawResolution("L9", "m2", "the vet went fine"), "no open loop"),
        (RawResolution("L1", "m2", "never said"), "quote"),
    ]
    for raw, why in raws:
        assert why in str(to_resolution(raw, labels, {"m2": said}))
    bot = _utt("the vet went fine", speaker=Speaker.COMPANION)
    raw = RawResolution("L1", "m2", "the vet went fine")
    assert "for real" in str(to_resolution(raw, labels, {"m2": bot}))


def test_open_loops_are_listed_for_the_model_and_resolutions_are_parsed() -> None:
    loop = _loop_from(_utt("going to the vet tomorrow"))
    shown = render_open_loops(loop_labels([loop]))
    assert "Open loops:" in shown
    assert "[L1] vet visit" in shown
    assert render_open_loops({}) == ""
    data: Json = {"resolved": [{"loop": "L1", "ref": "m2", "quote": "q"}, {"loop": 3}, "x"]}
    assert parse_resolved(data) == [RawResolution("L1", "m2", "q")]
    assert parse_resolved({"loops": []}) == []


def test_a_celebration_lands_on_the_day_and_encouragement_early_that_morning() -> None:
    assert follow_up_time("december 4th", "days", MON, UTC, LoopKind.CELEBRATE) == datetime(
        2026, 12, 4, 10, 0, tzinfo=UTC
    )
    assert follow_up_time("friday", "days", MON, UTC, LoopKind.ENCOURAGE) == datetime(
        2026, 10, 16, 8, 30, tzinfo=UTC
    )
    assert follow_up_time("friday", "days", MON, UTC) == _at(17)


def test_a_celebration_or_encouragement_without_a_day_after_today_is_not_recorded() -> None:
    for when in ("", "soon", "today"):
        raw = _raw(when=when, kind=LoopKind.CELEBRATE)
        assert "needs a day" in str(_make(raw, _utt("going to the vet tomorrow")))
    made = _make(_raw(when="friday", kind=LoopKind.ENCOURAGE), _utt("going to the vet tomorrow"))
    assert isinstance(made, OpenLoop)
    assert made.kind is LoopKind.ENCOURAGE


def test_a_same_day_plan_is_a_note_only_follow_up_a_few_hours_on() -> None:
    loop = _make(
        _raw(quote="exam in two hours", claim="their exam", scale="hours", kind="encourage"),
        _utt("exam in two hours"),
    )
    assert isinstance(loop, OpenLoop)
    assert loop.note_only
    assert loop.kind is LoopKind.FOLLOW_UP
    assert loop.follow_up_at == MON + NOTE_DELAY


def _loop(lid: str, kind: LoopKind, due: datetime, **over: object) -> OpenLoop:
    fields: dict[str, object] = {
        "id": lid,
        "relationship_id": REL,
        "claim": f"claim {lid}",
        "quote": "q",
        "source_utterance_id": UtteranceId("u1"),
        "follow_up_at": due,
        "sensitivity": 0,
        "created_at": due - timedelta(days=1),
        "kind": kind,
    }
    fields.update(over)
    return OpenLoop(**fields)  # type: ignore[arg-type]


def test_the_note_picks_a_celebration_first_then_the_latest_follow_up() -> None:
    now = _at(20, 15)
    loops = [
        _loop("old", LoopKind.FOLLOW_UP, _at(18)),
        _loop("new", LoopKind.FOLLOW_UP, _at(20)),
        _loop("bday", LoopKind.CELEBRATE, _at(20)),
        _loop("later", LoopKind.FOLLOW_UP, _at(21)),
    ]
    assert pick_note(loops, {}, now, UTC).id == "bday"  # type: ignore[union-attr]
    assert pick_note(loops[:2], {}, now, UTC).id == "new"  # type: ignore[union-attr]
    assert pick_note([loops[3]], {}, now, UTC) is None  # not due yet


def test_the_note_is_offered_twice_then_let_go_and_never_when_sensitive_or_settled() -> None:
    now = _at(20, 15)
    asked = _loop("a", LoopKind.FOLLOW_UP, _at(20), state=LoopState.ASKED)
    assert pick_note([asked], {}, now, UTC) is None  # asked by a reach-out, not a note
    assert pick_note([asked], {"a": 1}, now, UTC) is asked
    assert pick_note([asked], {"a": 2}, now, UTC) is None
    assert pick_note([_loop("s", LoopKind.FOLLOW_UP, _at(20), sensitivity=2)], {}, now, UTC) is None
    done = _loop("d", LoopKind.FOLLOW_UP, _at(20), state=LoopState.RESOLVED)
    assert pick_note([done], {}, now, UTC) is None
    stale = _loop("x", LoopKind.FOLLOW_UP, _at(15))
    assert pick_note([stale], {}, now, UTC) is None  # past the days a note keeps
    yesterday = _loop("y", LoopKind.CELEBRATE, _at(19))
    assert pick_note([yesterday], {}, now, UTC) is None  # a celebration is for its day only


def test_the_note_never_says_it_remembered_and_carries_the_claim() -> None:
    note = loop_note(_loop("a", LoopKind.FOLLOW_UP, _at(20), claim="the vet visit"))
    assert "the vet visit" in note
    assert "If it fits naturally" in note
