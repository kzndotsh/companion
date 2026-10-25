from __future__ import annotations

from datetime import UTC, datetime

from companion.core.clock import now_line


def test_the_clock_line_names_the_weekday_and_the_date() -> None:
    now = datetime(2026, 10, 24, 22, 0, tzinfo=UTC)
    local = now.astimezone()
    assert f"{local:%A} {local.day} {local:%B %Y}, {local:%H:%M}" in now_line(now, None)
