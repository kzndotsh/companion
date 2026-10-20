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


def _pairs(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> Path:
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    store.append_utterance(utterance(text="my dog is a pom. no wait, a papillon mix", uid="u1"))
    for bid, quote in (("pom", "my dog is a pom"), ("mix", "a papillon mix")):
        store.insert_belief(belief(bid=bid, utterance_id="u1", quote=quote, claim=f"dog {bid}"))
    store.add_memory_check(
        REL,
        belief(bid="pom").id,
        belief(bid="mix").id,
        ["replaces"] * 3,
        "replaces",
        prompt="p",
        at=T0,
    )
    store.close()
    return path


def test_a_conflicting_pair_keeps_the_one_the_owner_picks_and_retires_the_other(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _pairs(tmp_path, utterance, belief)
    asked: list[str] = []
    out = review(db, REL, ask=lambda q: asked.append(q) or "2")
    assert "1. dog pom" in asked[0] and "2. dog mix" in asked[0]
    assert "kept     dog mix" in out and "retired  dog pom" in out
    assert [b.id for b in Store(db).user_beliefs(REL)] == ["mix"]
    assert review(db, REL, ask=lambda _: "1") == "no questions about memory right now\n"


def test_keeping_both_of_a_pair_retires_nothing(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _pairs(tmp_path, utterance, belief)
    review(db, REL, ask=lambda _: "b")
    assert sorted(b.id for b in Store(db).user_beliefs(REL)) == ["mix", "pom"]
    assert Store(db).unanswered_checks(REL, ["replaces"]) == []


def test_a_pair_whose_memory_has_closed_is_not_asked(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _pairs(tmp_path, utterance, belief)
    store = Store(db)
    store.close_belief(belief(bid="pom").id, T0)
    store.close()
    assert "0 questions left" in review(db, REL, ask=lambda _: "1")
    assert [b.id for b in Store(db).user_beliefs(REL)] == ["mix"]


def test_skip_and_quit_leave_the_question_for_later(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _store(tmp_path, utterance, belief)
    answers = iter(["s", "q"])
    review(db, REL, ask=lambda _: next(answers))
    assert len(Store(db).unanswered_checks(REL, ["out_of_date", "overstated"])) == 2
