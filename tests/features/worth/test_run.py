from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from companion.core.extractor import Extraction
from companion.core.types import Belief, Json, Utterance
from companion.features.worth.run import expire_routine, label
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


class Labeller:
    """Labels each memory by a word in its claim."""

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, schema
        first = user.splitlines()[0]
        found = (
            "about_the_bot" if "feature" in first else "routine" if "dinner" in first else "keep"
        )
        return Extraction({"label": found}, "j", 0.0, 1)


def _store(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> Store:
    store = Store(tmp_path / "rel.sqlite")
    store.append_utterance(utterance(text="added a feature. had dinner. i love tea", uid="u1"))
    for bid, quote, claim in (
        ("bot", "added a feature", "Added a feature to the companion."),
        ("meal", "had dinner", "Had dinner on Monday."),
        ("tea", "i love tea", "Loves tea."),
    ):
        store.insert_belief(belief(bid=bid, utterance_id="u1", quote=quote, claim=claim))
    return store


async def test_a_new_remark_about_the_bot_is_dropped_and_a_routine_moment_leaves_after_a_week(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = _store(tmp_path, utterance, belief)
    done = await label(store, Labeller(), REL, T0, act_since=T0 - timedelta(days=1))
    assert (done.labelled, done.dropped, done.questions) == (3, 1, 0)
    assert sorted(b.id for b in store.user_beliefs(REL)) == ["meal", "tea"]
    assert expire_routine(store, REL, T0 + timedelta(days=3)) == 0
    assert expire_routine(store, REL, T0 + timedelta(days=8)) == 1
    assert [b.id for b in store.user_beliefs(REL)] == ["tea"]
    assert (await label(store, Labeller(), REL, T0, act_since=None)).labelled == 0


async def test_memories_kept_before_the_rule_become_questions_and_stay(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = _store(tmp_path, utterance, belief)
    done = await label(store, Labeller(), REL, T0, act_since=None)
    assert (done.dropped, done.questions) == (0, 2)
    assert len(store.user_beliefs(REL)) == 3
    assert {
        c.verdict for c in store.unanswered_checks(REL, ["ask_about_the_bot", "ask_routine"])
    } == {
        "ask_about_the_bot",
        "ask_routine",
    }
