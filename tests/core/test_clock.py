from __future__ import annotations

from datetime import UTC, datetime

import pytest

from companion.core.clock import local_zone, now_line


def test_the_clock_line_names_the_weekday_and_the_date() -> None:
    now = datetime(2026, 10, 24, 22, 0, tzinfo=UTC)
    local = now.astimezone(local_zone())
    assert f"{local:%A} {local.day} {local:%B %Y}, {local:%H:%M}" in now_line(now, None)


def test_the_local_zone_keeps_its_rules_across_a_clock_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TZ", "America/New_York")
    zone = local_zone()
    before = datetime(2026, 10, 27, 6, 49, tzinfo=UTC)  # daylight time, -04:00
    after = datetime(2026, 11, 2, 14, 3, tzinfo=UTC)  # standard time, -05:00
    assert before.astimezone(zone).hour == 2
    assert after.astimezone(zone).hour == 9


def test_without_a_named_zone_it_falls_back_to_the_current_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TZ", "Not/AZone")
    assert local_zone() == datetime.now().astimezone().tzinfo
