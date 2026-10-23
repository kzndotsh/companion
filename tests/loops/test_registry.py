from __future__ import annotations

from companion.loops import slow
from companion.loops.notes import SOURCES
from companion.loops.registry import FEATURES


def test_every_feature_part_is_run_where_it_belongs() -> None:
    names = [name for name, _ in SOURCES]
    for f in FEATURES:
        assert (f.note is not None) == (f.name in names), f.name
        if f.after_theirs is not None:
            assert f.after_theirs in slow.AFTER_THEIRS, f.name
        if f.after_own is not None:
            assert f.after_own in slow.AFTER_OWN, f.name
    assert len({f.name for f in FEATURES}) == len(FEATURES)
    assert not {f.name for f in FEATURES} & (set(names) - {f.name for f in FEATURES if f.note})
