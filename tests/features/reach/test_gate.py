from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from companion.core.rhythm import learn
from companion.features.reach.gate import Hold, Share, Situation, answer, hold, pace, share
from companion.features.reach.logic import Dial

NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
RHYTHM = learn([], NOW, UTC)


def _clear() -> Situation:
    """Nothing holds it."""
    return Situation(
        now=NOW,
        tz=UTC,
        rhythm=RHYTHM,
        dial=Dial.WARM,
        paced=None,
        last_message_at=NOW - timedelta(hours=13),
        in_scene=False,
        last_own=NOW - timedelta(days=2),
        unanswered=False,
        share=Share(1, 10),
        capped=False,
    )


# Each hold's trigger, in the order the gate checks them.
TRIGGERS: list[tuple[Hold, dict[str, object]]] = [
    (Hold.OFF, {"dial": Dial.OFF}),
    (Hold.CRISIS, {"crisis": True}),
    (Hold.QUIET, {"now": NOW.replace(hour=2)}),
    (Hold.SCENE, {"in_scene": True}),
    (Hold.ACTIVE, {"last_message_at": NOW - timedelta(minutes=30)}),
    (Hold.UNANSWERED, {"unanswered": True}),
    (Hold.GAP, {"last_own": NOW - timedelta(hours=5)}),
    (Hold.SHARE, {"share": Share(4, 10)}),
    (Hold.CAP, {"capped": True}),
]


def test_nothing_holds_a_clear_moment() -> None:
    assert hold(_clear()) is None


def test_the_first_hold_that_applies_is_the_reason() -> None:
    for i, (expected, _) in enumerate(TRIGGERS):
        over: dict[str, object] = {}
        for _, trigger in TRIGGERS[i:]:
            over.update(trigger)
        sit = replace(_clear(), **over)  # pyright: ignore[reportArgumentType]
        got = hold(sit)
        assert got is not None
        assert got[0] is expected, (expected, got)
        assert got[1]


def test_never_a_second_while_the_last_is_unanswered_however_long_ago() -> None:
    sit = replace(_clear(), unanswered=True, last_own=NOW - timedelta(days=5))
    got = hold(sit)
    assert got is not None
    assert got[0] is Hold.UNANSWERED


def test_the_share_is_held_at_the_dial() -> None:
    at_warm = replace(_clear(), share=Share(1, 3))
    under_warm = replace(_clear(), share=Share(1, 4))
    assert hold(at_warm) is not None
    assert hold(under_warm) is None
    assert hold(replace(under_warm, dial=Dial.LIGHT)) is not None  # 1/4 is over 1/5
    assert hold(replace(_clear(), share=Share(0, 0))) is None


def test_a_would_send_counts_as_a_conversation_it_started() -> None:
    t = NOW - timedelta(days=1)
    events = [
        (t, False),
        (t + timedelta(minutes=5), True),  # its reply, same conversation
        (t + timedelta(hours=4), True),  # its own reach-out starts one
        (t + timedelta(hours=9), False),
        (NOW - timedelta(days=20), True),  # outside two weeks
    ]
    assert share(events, NOW) == Share(1, 3)


def test_a_late_or_brief_answer_steps_the_dial_down_until_they_start_one() -> None:
    sent = NOW - timedelta(days=1)
    late = answer(sent, [(sent + timedelta(hours=20), "hey sorry, was out all day with friends")])
    brief = answer(sent, [(sent + timedelta(minutes=20), "haha yeah")])
    warm = answer(sent, [(sent + timedelta(minutes=20), "omg yes, it was so good, the ending!")])
    assert pace(late, RHYTHM, they_started_since=False) is not None
    assert pace(brief, RHYTHM, they_started_since=False) is not None
    assert pace(warm, RHYTHM, they_started_since=False) is None
    assert pace(brief, RHYTHM, they_started_since=True) is None
    paced = replace(_clear(), paced="answered briefly", share=Share(1, 4))
    assert paced.effective is Dial.NORMAL
    got = hold(paced)
    assert got is not None
    assert got[0] is Hold.SHARE  # 1/4 is at normal
    assert hold(replace(paced, paced=None)) is None  # 1/4 is under warm
