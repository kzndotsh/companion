from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tests.conftest import REL, T0

from companion.core.extractor import Extraction
from companion.core.types import Belief, Json, Utterance
from companion.loops.merging import propose
from companion.store.sqlite.store import Store


class Grouper:
    """Puts the first two memories together on every read, and writes a merge unless told not to."""

    def __init__(self, *, apart: bool = False) -> None:
        self.apart, self.calls = apart, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        self.calls += 1
        props = schema["properties"]
        assert isinstance(props, dict)
        if "groups" in props:
            return Extraction({"groups": [["m1", "m2"]]}, "j", 0.0, 1)
        return Extraction({"claim": "Has two dogs.", "keep_apart": self.apart}, "j", 0.0, 1)


def _store(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> tuple[Store, list[Belief]]:
    store = Store(tmp_path / "rel.sqlite")
    store.append_utterance(utterance(text="my dogs rex and bo. i like tea", uid="u1"))
    made = [
        belief(bid=bid, utterance_id="u1", quote=q, claim=c)
        for bid, q, c in (
            ("a", "my dogs rex", "Has a dog named Rex."),
            ("b", "and bo", "Has a dog named Bo."),
            ("c", "i like tea", "Likes tea."),
        )
    ]
    for b in made:
        store.insert_belief(b)
    return store, made


async def test_an_agreed_group_becomes_one_proposal_and_is_not_proposed_twice(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store, made = _store(tmp_path, utterance, belief)
    assert (await propose(store, Grouper(), REL, made, T0)).groups == 1
    [p] = store.merge_proposals(REL)
    assert (p.members, p.claim, p.answer) == ((made[0].id, made[1].id), "Has two dogs.", None)
    assert (await propose(store, Grouper(), REL, made, T0)).groups == 0
    assert len(store.user_beliefs(REL)) == 3  # nothing merges without the owner


async def test_keep_apart_from_the_writer_proposes_nothing(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store, made = _store(tmp_path, utterance, belief)
    assert (await propose(store, Grouper(apart=True), REL, made, T0)).groups == 0
    assert store.merge_proposals(REL) == []


async def test_a_pick_is_proposed_again_alone_with_new_wording(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.loops.merging import repick  # noqa: PLC0415

    store, made = _store(tmp_path, utterance, belief)
    first = store.add_merge_proposal(REL, [b.id for b in made], "all three", prompt="g", at=T0)
    store.answer_merge(first, "pick 1 2", T0)
    assert (await repick(store, Grouper(), REL, T0)).groups == 1
    assert store.merge_proposals(REL)[-1].members == (made[0].id, made[1].id)
    assert (await repick(store, Grouper(), REL, T0)).groups == 0
