from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, tzinfo

from companion.core.types import RelationshipId, UtteranceId
from companion.features.threads.gate import evaluate
from companion.features.threads.logic import Thread, ThreadKind, ThreadState

REL = RelationshipId("rel")
NOON = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def _loop(follow_up: datetime = NOON - timedelta(hours=2), **over: object) -> Thread:
    base = Thread(
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


def _at(now: datetime = NOON, held: str | None = None) -> tuple[datetime, tzinfo, str | None]:
    return now, UTC, held


def test_a_due_loop_with_nothing_in_the_way_is_sent_with_a_reason() -> None:
    v = evaluate([_loop()], *_at())
    assert v.send
    assert v.loop is not None
    assert "vet visit" in v.reason
    assert "due 2h ago" in v.reason


def test_nothing_is_due_before_its_time_or_when_there_are_no_loops() -> None:
    assert evaluate([], *_at()) == evaluate([], *_at())
    assert evaluate([], *_at()).reason == "nothing is due"
    not_yet = _loop(follow_up=NOON + timedelta(hours=1))
    assert not evaluate([not_yet], *_at()).send
    assert evaluate([not_yet], *_at()).reason == "nothing is due"


def test_a_sensitive_loop_is_never_picked_even_if_recorded() -> None:
    assert not evaluate([_loop(sensitivity=2)], *_at()).send


def test_only_open_loops_are_considered() -> None:
    for state in (
        ThreadState.ASKED,
        ThreadState.RESOLVED,
        ThreadState.EXPIRED,
        ThreadState.DROPPED,
    ):
        assert not evaluate([_loop(state=state)], *_at()).send


def test_the_oldest_due_loop_goes_first() -> None:
    old = _loop(follow_up=NOON - timedelta(hours=30), id="old", claim="haircut")
    new = _loop(follow_up=NOON - timedelta(hours=2), id="new")
    assert evaluate([new, old], *_at()).loop == old


def test_a_loop_past_its_horizon_is_reported_expired_and_not_sent() -> None:
    stale = _loop(follow_up=NOON - timedelta(days=3), id="stale")
    v = evaluate([stale], *_at())
    assert not v.send
    assert v.expired == (stale,)
    fresh = _loop(follow_up=NOON - timedelta(hours=2))
    both = evaluate([stale, fresh], *_at())
    assert both.send
    assert both.loop == fresh
    assert both.expired == (stale,)


def test_the_same_inputs_always_give_the_same_answer() -> None:
    loops = [_loop()]
    assert evaluate(loops, *_at()) == evaluate(loops, *_at())


def test_a_celebration_keeps_only_for_its_own_day() -> None:
    party = _loop(NOON - timedelta(hours=2), kind=ThreadKind.CELEBRATE)
    assert evaluate([party], *_at()).send
    next_day = evaluate([party], *_at(NOON + timedelta(days=1)))
    assert not next_day.send
    assert next_day.expired == (party,)
    follow = _loop(NOON - timedelta(hours=2))
    assert evaluate([follow], *_at(NOON + timedelta(days=1))).send


def test_a_note_only_loop_is_never_a_reach_out() -> None:
    assert not evaluate([_loop(note_only=True)], *_at()).send


def test_a_hold_from_the_shared_gate_holds_it_with_that_reason() -> None:
    v = evaluate([_loop()], *_at(held="9:00 is one of their quiet hours"))
    assert not v.send
    assert v.loop is not None
    assert v.reason == "9:00 is one of their quiet hours"
