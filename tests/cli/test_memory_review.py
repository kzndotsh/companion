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


def _merge_proposal(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> Path:
    from companion.core.types import BeliefKind  # noqa: PLC0415

    path = tmp_path / "rel.sqlite"
    store = Store(path)
    store.append_utterance(utterance(text="had my checkup, it was virtual. all done", uid="u1"))
    for bid, quote, kind in (
        ("visit", "had my checkup", BeliefKind.EVENT),
        ("virtual", "it was virtual", BeliefKind.EVENT),
        ("done", "all done", BeliefKind.STATE),
    ):
        store.insert_belief(
            belief(bid=bid, utterance_id="u1", quote=quote, claim=f"checkup {bid}", kind=kind)
        )
    ids = [belief(bid=b).id for b in ("visit", "virtual", "done")]
    store.add_memory_check(
        REL, ids[0], ids[1], ["contradicts"] * 3, "contradicts", prompt="p", at=T0
    )
    store.add_merge_proposal(REL, ids, "Had a virtual checkup and it is done.", prompt="g", at=T0)
    store.close()
    return path


def test_a_merge_joins_the_memories_keeping_every_quote_and_closes_the_originals(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.types import BeliefKind  # noqa: PLC0415

    db = _merge_proposal(tmp_path, utterance, belief)
    asked: list[str] = []
    out = review(db, REL, ask=lambda q: asked.append(q) or "m")
    assert "as one: Had a virtual checkup and it is done." in asked[0]
    assert len(asked) == 1  # the conflict between two of its pieces is never asked
    [merged] = Store(db).user_beliefs(REL)
    assert merged.claim == "Had a virtual checkup and it is done."
    assert {e.quote for e in merged.evidence} == {"had my checkup", "it was virtual", "all done"}
    assert merged.kind is BeliefKind.STATE  # it holds a passing state, so it fades like one
    assert "merged 3 into" in out


def test_keeping_a_merge_apart_changes_nothing_and_is_not_asked_again(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _merge_proposal(tmp_path, utterance, belief)
    answers = iter(["a", "b"])
    out = review(db, REL, ask=lambda _: next(answers))
    assert "kept apart  3 memories" in out
    assert len(Store(db).user_beliefs(REL)) == 3
    assert [p.answer for p in Store(db).merge_proposals(REL)] == ["apart"]


def test_it_asks_every_question_unless_capped(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _store(tmp_path, utterance, belief)
    assert "1 question left" in review(db, REL, ask=lambda _: "k", per_sitting=1)
    assert "0 questions left" in review(db, REL, ask=lambda _: "k")


def test_a_note_is_kept_and_the_merge_is_asked_again_with_it(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _merge_proposal(tmp_path, utterance, belief)
    answers = iter(["n", "too vague", "s"])
    asked: list[str] = []
    review(db, REL, ask=lambda q: asked.append(q) or next(answers))
    assert [p.answer for p in Store(db).merge_proposals(REL)] == ["note: too vague"]
    review(db, REL, ask=lambda q: asked.append(q) or "s")
    assert "your note: too vague" in asked[-1]


def test_their_own_wording_merges_with_it(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _merge_proposal(tmp_path, utterance, belief)
    answers = iter(["w", "Had a virtual checkup."])
    review(db, REL, ask=lambda _: next(answers))
    [merged] = Store(db).user_beliefs(REL)
    assert merged.claim == "Had a virtual checkup."
    assert len(merged.evidence) == 3


def test_a_pick_is_recorded_and_changes_nothing_yet(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    db = _merge_proposal(tmp_path, utterance, belief)
    answers = iter(["p", "1 2"])
    review(db, REL, ask=lambda _: next(answers))
    assert [p.answer for p in Store(db).merge_proposals(REL)] == ["pick 1 2"]
    assert len(Store(db).user_beliefs(REL)) == 3


def test_a_pick_needs_two_or_more_valid_numbers() -> None:
    from companion.cli.memory import picked  # noqa: PLC0415

    assert picked("1, 3", 3) == [0, 2]
    assert picked("2", 3) is None
    assert picked("1 4", 3) is None


def test_a_memory_labelled_about_the_bot_is_asked_and_retired_on_yes(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    store.append_utterance(utterance(text="added a feature", uid="u1"))
    store.insert_belief(belief(bid="bot", utterance_id="u1", quote="added a feature", claim="x"))
    store.add_memory_check(
        REL,
        belief(bid="bot").id,
        None,
        ["about_the_bot"] * 3,
        "ask_about_the_bot",
        prompt="w",
        at=T0,
    )
    store.close()
    asked: list[str] = []
    review(path, REL, ask=lambda q: asked.append(q) or "r")
    assert "remark about the bot" in asked[0]
    assert Store(path).user_beliefs(REL) == []
