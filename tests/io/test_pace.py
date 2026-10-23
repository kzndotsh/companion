from __future__ import annotations

import pytest

from companion.io.pace import (
    DEFAULT_PACE,
    MAX_SECONDS,
    PACES,
    hold_seconds,
    pace_factor,
    target_seconds,
)

REPLY = "pasta sounds more filling. what kind do you have?"  # 9 words


def test_a_longer_reply_takes_longer_to_type() -> None:
    short = target_seconds("hi there", "okay", 1.0)
    long = target_seconds("hi there", REPLY, 1.0)
    assert 0 < short < long


def test_a_longer_message_takes_longer_to_read() -> None:
    assert target_seconds("ok", REPLY, 1.0) < target_seconds("word " * 30, REPLY, 1.0)


def test_a_reaction_only_pays_the_reading_pause() -> None:
    assert target_seconds("ok", "", 1.0) < target_seconds("ok", REPLY, 1.0)
    assert target_seconds("ok", "", 1.0) > 0


def test_the_wait_is_capped_however_long_the_reply() -> None:
    assert target_seconds("word " * 200, "word " * 400, 1.6, jitter=1.25) == MAX_SECONDS


def test_the_model_time_already_spent_is_subtracted_and_never_goes_negative() -> None:
    full = target_seconds("hello", REPLY, 1.0)
    assert hold_seconds("hello", REPLY, 1.0, elapsed=1.0) == pytest.approx(full - 1.0)
    assert hold_seconds("hello", REPLY, 1.0, elapsed=60.0) == 0.0


def test_off_sends_at_once_and_slow_waits_longer() -> None:
    assert hold_seconds("hello", REPLY, PACES["off"], elapsed=0.0) == 0.0
    quick = target_seconds("hello", REPLY, PACES["quick"])
    natural = target_seconds("hello", REPLY, PACES["natural"])
    slow = target_seconds("hello", REPLY, PACES["slow"])
    assert quick < natural < slow


@pytest.mark.parametrize(
    ("raw", "factor"),
    [("off", 0.0), ("QUICK", 0.5), (" natural ", 1.0), ("slow", 1.6), ("", 1.0), ("fast", 1.0)],
)
def test_the_setting_names_map_to_factors_and_unknown_means_the_default(
    raw: str, factor: float
) -> None:
    assert pace_factor(raw) == factor
    assert DEFAULT_PACE in PACES
