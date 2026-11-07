from __future__ import annotations

from companion.core.reachout import PRECEDENCE
from companion.memory import memory_pass
from companion.registry import FEATURES
from companion.turn.notes import SOURCES


def test_every_feature_part_is_run_where_it_belongs() -> None:
    names = [name for name, *_ in SOURCES]
    for f in FEATURES:
        assert (f.note is not None) == (f.name in names), f.name
        if f.after_theirs is not None:
            assert f.after_theirs in memory_pass.AFTER_THEIRS, f.name
        if f.after_own is not None:
            assert f.after_own in memory_pass.AFTER_OWN, f.name
    assert len({f.name for f in FEATURES}) == len(FEATURES)
    assert not {f.name for f in FEATURES} & (set(names) - {f.name for f in FEATURES if f.note})


def test_the_steps_that_reach_out_first_are_ordered_by_the_one_precedence() -> None:
    from companion.kit.features import Move  # noqa: PLC0415

    class _Runtime:
        reach = None
        judge = None
        daily_cap_usd = None

    moves: list[Move] = []
    for f in FEATURES:
        if f.reaching is not None:
            moves += f.reaching(_Runtime())  # type: ignore[arg-type]
    ordered = sorted(moves, key=lambda m: m.rank)
    assert ordered[0].kind is None  # the shared gate first
    kinds = [m.kind for m in ordered if m.kind is not None]
    assert kinds == sorted(kinds, key=PRECEDENCE.index)
    assert set(kinds) >= set(PRECEDENCE[:2])  # a plan and a nudge before its own reasons
