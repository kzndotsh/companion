from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

from companion.core.history import gap_line, to_messages
from companion.core.types import Speaker, Utterance
from tests.conftest import T0


def test_a_pause_of_20_minutes_or_more_gets_a_line_and_a_shorter_one_does_not(
    utterance: Callable[..., Utterance],
) -> None:
    a = replace(utterance(text="remind me in 30"), at=T0)
    b = replace(
        utterance(text="hey, reminder", speaker=Speaker.COMPANION), at=T0 + timedelta(minutes=30)
    )
    c = replace(utterance(text="ha"), at=T0 + timedelta(minutes=31))
    got = to_messages([a, b, c])
    assert [m.role for m in got] == ["user", "system", "assistant", "user"]
    assert got[1].content.startswith("[30 minutes later, ")


def test_a_pause_before_the_message_being_answered_comes_last(
    utterance: Callable[..., Utterance],
) -> None:
    a = replace(utterance(text="night"), at=T0)
    assert to_messages([a], T0 + timedelta(minutes=5))[-1].role == "user"
    got = to_messages([a], T0 + timedelta(hours=3))
    assert got[-1].role == "system"
    assert "later" in got[-1].content or "next day" in got[-1].content


def test_the_line_names_the_day_change_and_never_says_ago() -> None:
    line = gap_line(T0, T0 + timedelta(days=3))
    assert line is not None
    assert "3 days later" in line
    assert "ago" not in (gap_line(T0, T0 + timedelta(hours=5)) or "")
    assert gap_line(T0, T0 + timedelta(minutes=19)) is None
