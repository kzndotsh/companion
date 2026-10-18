from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from companion.core.openloops import (
    Making,
    OpenLoop,
    RawLoop,
    RawResolution,
    follow_up_time,
    loop_labels,
    parse,
    parse_resolved,
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
        (_raw(scale="hours"), "going to the vet tomorrow", "same-day"),
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
