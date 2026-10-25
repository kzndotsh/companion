from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
from companion.features.threads.logic import (
    NOTE_DELAY,
    Making,
    Met,
    RawLoop,
    RawResolution,
    Thread,
    ThreadKind,
    ThreadState,
    follow_up_time,
    loop_labels,
    loop_note,
    pace,
    pace_holds,
    parse,
    parse_met,
    parse_resolved,
    pick_note,
    render_open_loops,
    repeats,
    to_loop,
    to_resolution,
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


def _make(raw: RawLoop, u: Utterance, now: datetime = MON) -> Thread | str:
    made = Making(REL, now, UTC, lambda: "loop-1")
    return to_loop(raw, {"m1": u}, made)


def test_a_good_loop_keeps_the_exact_quote_and_gets_its_follow_up_time() -> None:
    loop = _make(_raw(), _utt("ok so i'm Going To The Vet tomorrow, wish me luck"))
    assert isinstance(loop, Thread)
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
        to_loop(_raw(ref="m9"), {"m1": _utt("going to the vet tomorrow")}, made), Thread
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


def _loop_from(u: Utterance) -> Thread:
    made = Making(REL, MON, UTC, lambda: "loop-1")
    loop = to_loop(_raw(), {"m1": u}, made)
    assert isinstance(loop, Thread)
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
    assert follow_up_time("december 4th", "days", MON, UTC, ThreadKind.CELEBRATE) == datetime(
        2026, 12, 4, 10, 0, tzinfo=UTC
    )
    assert follow_up_time("friday", "days", MON, UTC, ThreadKind.ENCOURAGE) == datetime(
        2026, 10, 16, 8, 30, tzinfo=UTC
    )
    assert follow_up_time("friday", "days", MON, UTC) == _at(17)


def test_a_celebration_or_encouragement_without_a_day_after_today_is_not_recorded() -> None:
    for when in ("", "soon", "today"):
        raw = _raw(when=when, kind=ThreadKind.CELEBRATE)
        assert "needs a day" in str(_make(raw, _utt("going to the vet tomorrow")))
    made = _make(_raw(when="friday", kind=ThreadKind.ENCOURAGE), _utt("going to the vet tomorrow"))
    assert isinstance(made, Thread)
    assert made.kind is ThreadKind.ENCOURAGE


def test_a_same_day_plan_is_a_note_only_follow_up_a_few_hours_on() -> None:
    loop = _make(
        _raw(quote="exam in two hours", claim="their exam", scale="hours", kind="encourage"),
        _utt("exam in two hours"),
    )
    assert isinstance(loop, Thread)
    assert loop.note_only
    assert loop.kind is ThreadKind.FOLLOW_UP
    assert loop.follow_up_at == MON + NOTE_DELAY


def _loop(lid: str, kind: ThreadKind, due: datetime, **over: object) -> Thread:
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
    return Thread(**fields)  # type: ignore[arg-type]


def test_the_note_picks_a_celebration_first_then_the_latest_follow_up() -> None:
    now = _at(20, 15)
    loops = [
        _loop("old", ThreadKind.FOLLOW_UP, _at(18)),
        _loop("new", ThreadKind.FOLLOW_UP, _at(20)),
        _loop("bday", ThreadKind.CELEBRATE, _at(20)),
        _loop("later", ThreadKind.FOLLOW_UP, _at(21)),
    ]
    assert pick_note(loops, {}, now, UTC).id == "bday"  # type: ignore[union-attr]
    assert pick_note(loops[:2], {}, now, UTC).id == "new"  # type: ignore[union-attr]
    assert pick_note([loops[3]], {}, now, UTC) is None  # not due yet


def test_the_note_is_offered_twice_then_let_go_and_never_when_sensitive_or_settled() -> None:
    now = _at(20, 15)
    asked = _loop("a", ThreadKind.FOLLOW_UP, _at(20), state=ThreadState.ASKED)
    assert pick_note([asked], {}, now, UTC) is None  # asked by a reach-out, not a note
    assert pick_note([asked], {"a": 1}, now, UTC) is asked
    assert pick_note([asked], {"a": 2}, now, UTC) is None
    assert (
        pick_note([_loop("s", ThreadKind.FOLLOW_UP, _at(20), sensitivity=2)], {}, now, UTC) is None
    )
    done = _loop("d", ThreadKind.FOLLOW_UP, _at(20), state=ThreadState.RESOLVED)
    assert pick_note([done], {}, now, UTC) is None
    stale = _loop("x", ThreadKind.FOLLOW_UP, _at(15))
    assert pick_note([stale], {}, now, UTC) is None  # past the days a note keeps
    yesterday = _loop("y", ThreadKind.CELEBRATE, _at(19))
    assert pick_note([yesterday], {}, now, UTC) is None  # a celebration is for its day only


def test_the_note_never_says_it_remembered_and_carries_the_claim() -> None:
    note = loop_note(_loop("a", ThreadKind.FOLLOW_UP, _at(20), claim="the vet visit"))
    assert "the vet visit" in note
    assert "If it fits naturally" in note


def _loose(raw: RawLoop, u: Utterance) -> Thread | str:
    return to_loop(raw, {"m1": u}, Making(REL, MON, UTC, lambda: "loop-1", loose=True))


def test_a_hedged_plan_is_a_note_only_loop_when_loose_and_rejected_when_strict() -> None:
    u = _utt("going to the vet tomorrow")
    maybe = _raw(certainty="maybe")
    loose = _loose(maybe, u)
    assert isinstance(loose, Thread)
    assert loose.note_only  # asked when they write, never a reach-out
    assert _make(maybe, u) == "not a firm plan (maybe), a friend would not ask"
    assert _loose(_raw(certainty="wish"), u) == "not a firm plan (wish), a friend would not ask"
    firm = _loose(_raw(), u)
    assert isinstance(firm, Thread)
    assert not firm.note_only


def test_a_sensitive_item_is_rejected_as_sensitive_whatever_else_is_wrong() -> None:
    u = _utt("going to the vet tomorrow")
    hedged_and_sensitive = _raw(certainty="maybe", sensitivity=2, scale="minutes")
    assert _make(hedged_and_sensitive, u) == "sensitive, never raised on its own"
    assert _loose(hedged_and_sensitive, u) == "sensitive, never raised on its own"


def test_the_pace_starts_at_a_day_and_moves_with_how_they_meet_threads() -> None:
    assert pace([]) == timedelta(hours=24)
    assert pace([Met.PICKED_UP]) == timedelta(hours=16)
    assert pace([Met.PICKED_UP] * 9) == timedelta(hours=4)
    assert pace([Met.BRUSHED_OFF]) == timedelta(hours=48)
    assert pace([Met.IGNORED]) == timedelta(hours=96)
    assert pace([Met.IGNORED, Met.PICKED_UP]) == timedelta(hours=48)  # the newest moves it back


def test_the_pace_waits_its_time_and_never_passes_the_ceiling() -> None:
    now = datetime(2026, 10, 25, 12, tzinfo=UTC)
    wait = timedelta(hours=4)
    assert pace_holds(wait, [], now) is None
    assert pace_holds(wait, [now - timedelta(hours=3)], now) is not None
    assert pace_holds(wait, [now - timedelta(hours=5)], now) is None
    three = [now - timedelta(hours=h) for h in (5, 10, 15)]
    assert "ceiling" in (pace_holds(wait, three, now) or "")
    assert parse_met({"met": "ignored"}) is Met.IGNORED
    assert parse_met({"met": "maybe"}) is None


def test_a_repeat_of_the_same_kind_is_named_and_another_kind_is_not() -> None:
    due = datetime(2026, 10, 20, 10, tzinfo=UTC)
    open_loop = _loop("a", ThreadKind.FOLLOW_UP, due)
    labels = {"L1": open_loop}
    assert "open loop" in (repeats(_raw(same_as="L1"), labels, {}) or "")
    assert repeats(_raw(same_as="L1", kind="celebrate"), labels, {}) is None
    assert "N1" in (repeats(_raw(same_as="N1"), {}, {"N1": "follow_up"}) or "")
    assert repeats(_raw(same_as="N2"), labels, {"N1": "follow_up"}) is None
    assert repeats(_raw(), labels, {"N1": "follow_up"}) is None


def test_same_as_is_read_from_the_answer_and_may_be_missing() -> None:
    item: dict[str, Json] = {
        "ref": "m1",
        "quote": "q",
        "claim": "c",
        "when": "",
        "scale": "days",
        "sensitivity": 0,
        "certainty": "firm",
        "about_companion": False,
        "kind": "follow_up",
    }
    assert (parse({"loops": [item | {"same_as": " l2 "}]}) or [])[0].same_as == "L2"
    assert (parse({"loops": [item]}) or [])[0].same_as == ""
