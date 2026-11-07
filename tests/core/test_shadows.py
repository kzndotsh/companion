from __future__ import annotations

from datetime import date

from companion.core.shadows import SHADOWS, overdue
from companion.core.switch import SWITCHES, Mode


def test_every_setting_that_defaults_to_shadow_has_a_review_date() -> None:
    shadowed = {s for s in SWITCHES if s.values[0] == Mode.SHADOW}
    listed = {s.switch for s in SHADOWS}
    missing = [s.label for s in shadowed - listed]
    assert not missing, f"add a row to core/shadows.py for: {missing}"


def test_a_feature_is_overdue_the_day_after_its_review() -> None:
    first = min(s.review_by for s in SHADOWS)
    assert not overdue(first)
    assert overdue(date.fromordinal(first.toordinal() + 1))
