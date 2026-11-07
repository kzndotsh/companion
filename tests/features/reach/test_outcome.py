from __future__ import annotations

from datetime import UTC, datetime, timedelta

from companion.core.reachout import Fate, Kind, ReachRecord
from companion.core.types import Json
from companion.features.reach.outcome import Landed, outcome, stopped, summary

AT = datetime(2026, 11, 1, 15, 0, tzinfo=UTC)
SENT = ReachRecord("r1", Kind.THOUGHT, Fate.LIVE, "saw a cat that looked like yours", AT)
H = timedelta(hours=1)


def test_open_while_they_have_not_answered_and_two_days_have_not_passed() -> None:
    assert outcome(SENT, [], AT + 47 * H) is None


def test_unanswered_after_two_days() -> None:
    got = outcome(SENT, [], AT + 48 * H)
    assert got is not None
    assert got.got is None
    assert got.detail(None)["answered"] is False


def test_an_answer_after_two_days_counts_as_unanswered() -> None:
    got = outcome(SENT, [(AT + 50 * H, "oh hey")], AT + 51 * H)
    assert got is not None
    assert got.got is None


def test_an_answer_waits_until_it_is_all_in() -> None:
    theirs = [(AT + 2 * H, "omg"), (AT + 2 * H + timedelta(minutes=3), "show me")]
    assert outcome(SENT, theirs, AT + 2 * H + timedelta(minutes=5)) is None
    got = outcome(SENT, theirs, AT + 3 * H)
    assert got is not None
    assert got.reply == "omg show me"
    detail = got.detail(Landed.PICKED_UP)
    assert (detail["answered"], detail["after_hours"], detail["words"]) == (True, 2.0, 3)
    assert detail["landed"] == "picked_up"


def test_a_message_before_it_is_not_an_answer() -> None:
    assert outcome(SENT, [(AT - H, "night")], AT + H) is None


def test_a_shadow_record_is_the_base_rate_and_never_read() -> None:
    shadow = ReachRecord("r2", Kind.MISSING, Fate.SHADOW, "hi", AT)
    got = outcome(shadow, [(AT + 9 * H, "back")], AT + 10 * H)
    assert got is not None
    detail = got.detail(None)
    assert (detail["mode"], detail["base_rate"], detail["landed"]) == ("shadow", True, None)


def test_a_live_answer_that_could_not_be_read_says_so() -> None:
    got = outcome(SENT, [(AT + H, "hey")], AT + 2 * H)
    assert got is not None
    assert got.detail(None)["landed"] == "not read"


def test_a_stop_stands_until_resumed_after_it() -> None:
    assert not stopped([], [])
    assert stopped([AT], [])
    assert not stopped([AT], [AT + H])
    assert stopped([AT, AT + 2 * H], [AT + H])


def test_the_summary_groups_by_kind_and_mode() -> None:
    def rec(kind: Kind, mode: str, hours: float | None, landed: str | None) -> dict[str, Json]:
        return {
            "kind": kind.value,
            "mode": mode,
            "answered": hours is not None,
            "after_hours": hours,
            "landed": landed,
        }

    lines = summary(
        [
            rec(Kind.THOUGHT, "shadow", 9.0, None),
            rec(Kind.THOUGHT, "shadow", None, None),
            rec(Kind.THOUGHT, "live", 1.0, "picked_up"),
        ]
    )
    assert any(
        "live" in line and "1 of 1 answered" in line and "1 picked_up" in line for line in lines
    )
    assert any("shadow" in line and "1 of 2 answered, median 9.0h" in line for line in lines)
