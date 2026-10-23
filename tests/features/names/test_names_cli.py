from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from companion.core.types import Belief, Utterance
from companion.features.names.cli import run
from companion.features.names.logic import Row
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def test_the_list_shows_each_name_with_its_words_and_what_is_left_to_read(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = tmp_path / "rel.sqlite"
    store = Store(db)
    store.append_utterance(utterance(text="biscuit hates baths", uid="u1"))
    for bid in ("b1", "b2"):
        store.insert_belief(belief(bid=bid, utterance_id="u1", quote="biscuit hates baths"))
    assert "2 memories not read" in run(db, REL)
    one = belief(bid="b1").id
    store.add_names(
        REL, [Row(one, "Biscuit", ("biscuit", "bis"))], [one], model="m", prompt="p", at=T0
    )
    store.close()
    out = run(db, REL)
    assert "  1  Biscuit  (bis, biscuit)" in out
    assert "1 memories not read yet" in out
