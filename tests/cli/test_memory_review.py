from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tests.conftest import REL, T0

from companion.cli.memory import review
from companion.core.types import Belief, Utterance
from companion.store.sqlite.store import Store


def _store(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> Path:
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    store.append_utterance(
        utterance(text="job hunting is rough and i always eat burgers", uid="u1")
    )
    for bid, quote, verdict in (
        ("job", "job hunting is rough", "out_of_date"),
        ("burger", "i always eat burgers", "overstated"),
    ):
        store.insert_belief(belief(bid=bid, utterance_id="u1", quote=quote, claim=f"claim {bid}"))
        store.add_memory_check(
            REL, belief(bid=bid).id, None, [verdict] * 3, verdict, prompt="p", at=T0
        )
    store.close()
    return path


def test_retire_and_keep_are_recorded_and_not_asked_again(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _store(tmp_path, utterance, belief)
    answers = iter(["r", "k"])
    out = review(db, REL, ask=lambda _: next(answers))
    assert "retired  claim job" in out
    assert "kept     claim burger" in out
    assert [b.id for b in Store(db).user_beliefs(REL)] == ["burger"]
    assert review(db, REL, ask=lambda _: "r") == "no questions about memory right now\n"


def test_skip_and_quit_leave_the_question_for_later(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _store(tmp_path, utterance, belief)
    answers = iter(["s", "q"])
    review(db, REL, ask=lambda _: next(answers))
    assert len(Store(db).unanswered_checks(REL, ["out_of_date", "overstated"])) == 2
