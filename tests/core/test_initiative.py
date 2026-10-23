from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from companion.core.initiative import Situation, evaluate
from companion.core.openloops import LoopKind, LoopState, OpenLoop
from companion.core.reachout import Caps, in_quiet_hours
from companion.core.types import RelationshipId, UtteranceId

REL = RelationshipId("rel")
NOON = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def _loop(follow_up: datetime = NOON - timedelta(hours=2), **over: object) -> OpenLoop:
    base = OpenLoop(
        "l1",
        REL,
        "vet visit",
        "the vet tomorrow",
        UtteranceId("u1"),
        follow_up,
        0,
        follow_up - timedelta(days=2),
    )
    return replace(base, **over)  # type: ignore[arg-type]


def _sit(**over: object) -> Situation:
    base = Situation(
        now=NOON,
        tz=UTC,
        last_message_at=NOON - timedelta(hours=5),
        in_scene=False,
        sent_today=0,
        last_reach_out_at=None,
    )
    return replace(base, **over)  # type: ignore[arg-type]


def test_a_due_loop_with_nothing_in_the_way_is_sent_with_a_reason() -> None:
    v = evaluate([_loop()], _sit())
    assert v.send
    assert v.loop is not None
    assert "vet visit" in v.reason
    assert "due 2h ago" in v.reason


def test_nothing_is_due_before_its_time_or_when_there_are_no_loops() -> None:
    assert evaluate([], _sit()) == evaluate([], _sit())
    assert evaluate([], _sit()).reason == "nothing is due"
    not_yet = _loop(follow_up=NOON + timedelta(hours=1))
    assert not evaluate([not_yet], _sit()).send
    assert evaluate([not_yet], _sit()).reason == "nothing is due"


def test_quiet_hours_hold_it_and_the_reason_names_them() -> None:
    late = NOON.replace(hour=23, minute=30)
    v = evaluate([_loop()], _sit(now=late, last_message_at=late - timedelta(hours=5)))
    assert not v.send
    assert v.reason == "quiet hours, 11:00 PM to 8:00 AM"
    assert v.loop is not None  # held, not dropped


def test_quiet_hours_wrap_past_midnight_and_end_in_the_morning() -> None:
    caps = Caps()
    assert in_quiet_hours(NOON.replace(hour=2), UTC, caps)
    assert in_quiet_hours(NOON.replace(hour=23), UTC, caps)
    assert not in_quiet_hours(NOON.replace(hour=8), UTC, caps)
    assert not in_quiet_hours(NOON.replace(hour=22, minute=59), UTC, caps)


def test_quiet_hours_use_their_zone_not_utc() -> None:
    from datetime import timezone  # noqa: PLC0415

    east = timezone(timedelta(hours=-4))
    # 12:00 UTC is 08:00 in the east, the first minute that is not quiet; 11:59 is still quiet
    assert not in_quiet_hours(NOON, east, Caps())
    assert in_quiet_hours(NOON - timedelta(minutes=1), east, Caps())


def test_each_hold_has_its_own_named_reason() -> None:
    assert "scene" in evaluate([_loop()], _sit(in_scene=True)).reason
    assert "already reached out today" in evaluate([_loop()], _sit(sent_today=1)).reason
    gap = evaluate([_loop()], _sit(last_reach_out_at=NOON - timedelta(hours=5)))
    assert "5h ago, under the 20h minimum" in gap.reason
    active = evaluate([_loop()], _sit(last_message_at=NOON - timedelta(minutes=30)))
    assert "active 30 minutes ago" in active.reason
    for v in (evaluate([_loop()], _sit(in_scene=True)), gap, active):
        assert not v.send


def test_a_sensitive_loop_is_never_picked_even_if_recorded() -> None:
    assert not evaluate([_loop(sensitivity=2)], _sit()).send


def test_only_open_loops_are_considered() -> None:
    for state in (LoopState.ASKED, LoopState.RESOLVED, LoopState.EXPIRED, LoopState.DROPPED):
        assert not evaluate([_loop(state=state)], _sit()).send


def test_the_oldest_due_loop_goes_first() -> None:
    old = _loop(follow_up=NOON - timedelta(hours=30), id="old", claim="haircut")
    new = _loop(follow_up=NOON - timedelta(hours=2), id="new")
    assert evaluate([new, old], _sit()).loop == old


def test_a_loop_past_its_horizon_is_reported_expired_and_not_sent() -> None:
    stale = _loop(follow_up=NOON - timedelta(days=3), id="stale")
    v = evaluate([stale], _sit())
    assert not v.send
    assert v.expired == (stale,)
    fresh = _loop(follow_up=NOON - timedelta(hours=2))
    both = evaluate([stale, fresh], _sit())
    assert both.send
    assert both.loop == fresh
    assert both.expired == (stale,)


def test_the_same_inputs_always_give_the_same_answer() -> None:
    loops = [_loop()]
    assert evaluate(loops, _sit()) == evaluate(loops, _sit())


def test_after_an_unanswered_reach_out_it_waits_longer_and_after_two_it_stops() -> None:
    yesterday = NOON - timedelta(hours=30)
    answered = evaluate([_loop()], _sit(last_reach_out_at=yesterday))
    assert answered.send
    once = evaluate([_loop()], _sit(last_reach_out_at=yesterday, unanswered=1))
    assert not once.send
    assert "went unanswered; waits 72h before another (30h so far)" in once.reason
    later = evaluate([_loop()], _sit(last_reach_out_at=NOON - timedelta(hours=80), unanswered=1))
    assert later.send
    twice = evaluate([_loop()], _sit(last_reach_out_at=NOON - timedelta(days=9), unanswered=2))
    assert not twice.send
    assert "waits for them to write first" in twice.reason


def test_a_celebration_keeps_only_for_its_own_day() -> None:
    party = _loop(NOON - timedelta(hours=2), kind=LoopKind.CELEBRATE)
    assert evaluate([party], _sit()).send
    next_day = evaluate([party], _sit(now=NOON + timedelta(days=1)))
    assert not next_day.send
    assert next_day.expired == (party,)
    follow = _loop(NOON - timedelta(hours=2))
    assert evaluate([follow], _sit(now=NOON + timedelta(days=1))).send


def test_a_note_only_loop_is_never_a_reach_out() -> None:
    assert not evaluate([_loop(note_only=True)], _sit()).send
