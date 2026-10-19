from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, timedelta
from pathlib import Path

import pytest
from tests.conftest import REL, T0

from companion.core.extractor import Extraction
from companion.core.knowing import Depth, Domain, Label
from companion.core.types import Belief, BeliefKind, Json, Utterance
from companion.loops.consolidate import nightly
from companion.store.sqlite.store import Store

LATER = T0 + timedelta(days=10)


class Judge:
    def __init__(self, label: str) -> None:
        self.label, self.calls = label, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"label": self.label}, "j", 0.0, 1)


@pytest.fixture
def spill(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> tuple[Store, Belief]:
    store = Store(tmp_path / "rel.sqlite")
    u = utterance(text="my coffee went everywhere", uid="u1")
    store.append_utterance(u)
    b = belief(
        bid="spill",
        utterance_id="u1",
        quote="my coffee went everywhere",
        kind=BeliefKind.EVENT,
        claim="On day one the user spilled coffee.",
    )
    store.insert_belief(b)
    store.add_belief_labels(REL, [Label(b.id, Domain.DAILY, Depth.SURFACE)], "m", "p", T0)
    return store, b


async def test_in_shadow_a_faded_passing_moment_is_logged_not_closed(
    spill: tuple[Store, Belief],
) -> None:
    store, _ = spill
    night = await nightly(store, Judge("passing"), REL, LATER, UTC, mode="shadow")
    assert (night.checked, night.closed) == (1, 1)
    assert [b.id for b in store.user_beliefs(REL)] == ["spill"]


async def test_on_it_closes_and_never_reads_the_same_memory_twice(
    spill: tuple[Store, Belief],
) -> None:
    store, _ = spill
    judge = Judge("passing")
    await nightly(store, judge, REL, LATER, UTC, mode="on")
    assert store.user_beliefs(REL) == []
    calls = judge.calls
    await nightly(store, judge, REL, LATER + timedelta(days=1), UTC, mode="on")
    assert judge.calls == calls


async def test_out_of_date_is_a_question_and_a_young_memory_waits(
    spill: tuple[Store, Belief],
) -> None:
    store, _ = spill
    judge = Judge("out_of_date")
    assert (await nightly(store, judge, REL, T0 + timedelta(days=3), UTC, mode="on")).checked == 0
    night = await nightly(store, judge, REL, LATER, UTC, mode="on")
    assert (night.closed, night.questions) == (0, 1)
    assert [c.belief_id for c in store.unanswered_checks(REL, ["out_of_date"])] == ["spill"]
