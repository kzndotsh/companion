from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from companion.core.types import Belief, BeliefId, Utterance
from companion.features.upkeep.reread.store import MemoryChecks
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def test_a_renamed_check_keeps_what_it_read_and_a_new_version_reads_again(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    said = utterance(uid="u1")
    store.append_utterance(said)
    for bid in ("a", "b", "c"):
        store.insert_belief(belief(bid=bid))
    store.part(MemoryChecks).add(REL, BeliefId("a"), None, ["keep"], "keep", prompt="old@v1", at=T0)
    store.part(MemoryChecks).add(REL, BeliefId("b"), None, ["keep"], "keep", prompt="new@v2", at=T0)
    store.part(MemoryChecks).add(
        REL, BeliefId("c"), None, ["keep"], "keep", prompt="other@v2", at=T0
    )
    assert store.part(MemoryChecks).checked(REL, ("old", "new")) == {"a", "b"}
    assert store.part(MemoryChecks).checked(REL, ("old", "new"), "v2") == {"b"}
