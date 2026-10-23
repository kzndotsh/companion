from __future__ import annotations

from datetime import date

from companion.core.shadows import SHADOWS, overdue
from companion.settings import SWITCHES


def test_every_setting_that_defaults_to_shadow_has_a_review_date() -> None:
    shadowed = {s.label for s in SWITCHES if s.values[0] == "shadow"}
    listed = {s.switch for s in SHADOWS}
    assert shadowed <= listed, f"add a row to core/shadows.py for: {shadowed - listed}"


def test_a_feature_is_overdue_the_day_after_its_review() -> None:
    first = min(s.review_by for s in SHADOWS)
    assert not overdue(first)
    assert overdue(date.fromordinal(first.toordinal() + 1))
