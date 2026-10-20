from __future__ import annotations

from datetime import timedelta

from companion.core.hooks import Basic, agreed, may_ask, read_basic
from tests.conftest import T0


def test_a_basic_counts_only_when_every_read_names_it() -> None:
    assert agreed([Basic.AGE, Basic.AGE, Basic.AGE]) is Basic.AGE
    assert agreed([Basic.AGE, Basic.WORK, Basic.AGE]) is None
    assert agreed([Basic.AGE, None, Basic.AGE]) is None
    assert read_basic({"basic": "none"}) is None
    assert read_basic({"basic": "place"}) is Basic.PLACE


def test_the_gate_allows_one_hook_a_day_and_each_basic_twice() -> None:
    assert may_ask(Basic.AGE, [], T0)
    assert not may_ask(None, [], T0)
    assert not may_ask(Basic.AGE, [("work", T0 - timedelta(hours=3))], T0)  # one a day, any basic
    twice = [("age", T0 - timedelta(days=9)), ("age", T0 - timedelta(days=4))]
    assert not may_ask(Basic.AGE, twice, T0)
    assert may_ask(Basic.WORK, twice, T0)
