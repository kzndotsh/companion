from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.types import Frame, Json, Speaker, Utterance
from companion.features.promises.cli import run
from companion.features.promises.logic import (
    MOMENT_DAYS,
    Proposed,
    Scope,
    agreed,
    in_force,
    parse,
    to_promise,
)
from companion.features.promises.run import read_promises
from companion.features.threads.run import Reading, catch_up_loops
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0

SORRY = "sorry! i won't call you buddy again, promise"


class Reads:
    """Answers each call with the promise in the newest companion message, failing `fails` first."""

    def __init__(self, fails: int = 0) -> None:
        self.fails, self.calls = fails, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, schema
        self.calls += 1
        if self.calls <= self.fails:
            msg = "down"
            raise RuntimeError(msg)
        label = next(
            (line.split("]")[0][1:] for line in user.splitlines() if "COMPANION TARGET" in line),
            None,
        )
        found: list[Json] = (
            [
                {
                    "message": label,
                    "quote": "i won't call you buddy again",
                    "claim": "The companion won't call them buddy.",
                    "kind": "standing",
                    "avoid": "buddy",
                }
            ]
            if label
            else []
        )
        return Extraction(data={"promises": found}, model="fake", cost_usd=0.0, latency_ms=1)


def _window(
    utterance: Callable[..., Utterance], text: str, frame: Frame = Frame.REAL
) -> dict[str, Utterance]:
    said = utterance(text="don't call me buddy pls")
    reply = utterance(text=text, speaker=Speaker.COMPANION, frame=frame)
    return {"m1": said, "m2": reply}


def _proposed(
    quote: str, avoid: str = "", message: str = "m2", *, checkable: bool = True
) -> Proposed:
    claim = "The companion won't call them buddy."
    return Proposed(message, quote, claim, "standing", avoid, checkable=checkable)


def test_a_promise_is_kept_only_when_code_finds_it_in_its_own_forward_looking_words(
    utterance: Callable[..., Utterance],
) -> None:
    window = _window(utterance, SORRY)
    kept = to_promise(_proposed("i won't call you buddy again", "buddy"), window, "p1")
    assert not isinstance(kept, str)
    assert kept.avoid == "buddy"
    cases = {
        "quote not in the message": _proposed("i will never say buddy"),
        "not one of its own messages": _proposed("don't call me buddy", message="m1"),
        "the word to avoid is not in the exchange": _proposed("i won't call you buddy", "pal"),
    }
    for why, p in cases.items():
        assert to_promise(p, window, "p") == why
    assert to_promise(_proposed("sorry!"), window, "p") == "nothing in it looks forward"
    vague = _proposed("i won't call you buddy again", checkable=False)
    assert to_promise(vague, window, "p") == "nothing in it a later reply could keep or break"
    hedged = _window(utterance, "i'll try not to call you buddy again")
    assert to_promise(_proposed("i'll try not to call you buddy"), hedged, "p") == "hedged"
    scene = _window(utterance, SORRY, Frame.PLAY)
    assert to_promise(_proposed("i won't call you buddy again"), scene, "p") == (
        "said in a pretend scene"
    )


@pytest.fixture
def store(tmp_path: Path, utterance: Callable[..., Utterance]) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    s.append_utterance(utterance(text="don't call me buddy pls"))
    s.append_utterance(utterance(text=SORRY, speaker=Speaker.COMPANION))
    return s


async def _catch_up(store: Store, model: Reads, *, promises: bool = True) -> None:
    await catch_up_loops(
        store,
        model,
        REL,
        (T0, UTC),
        lambda r, d: None,
        Reading(40, 4, 1, promises=read_promises if promises else None),
    )


async def test_its_promise_is_recorded_once_and_a_failed_read_is_tried_again(
    store: Store,
) -> None:
    model = Reads(fails=2)  # the loop read and the promise read both fail the first time
    await _catch_up(store, model)
    assert store.promises(REL) == []
    assert store.loop_cursor(REL) is None
    await _catch_up(store, model)
    assert [r.promise.avoid for r in store.promises(REL)] == ["buddy"]
    await _catch_up(store, Reads())
    assert len(store.promises(REL)) == 1


async def test_off_reads_no_promises(store: Store) -> None:
    await _catch_up(store, Reads(), promises=False)
    assert store.promises(REL) == []


async def test_the_owner_can_mark_one_not_a_promise_and_it_leaves_the_list(
    store: Store, tmp_path: Path
) -> None:
    await _catch_up(store, Reads())
    store.close()
    db = tmp_path / "rel.sqlite"
    assert "avoid 'buddy'" in run(db, REL)
    pid = Store(db).promises(REL)[0].promise.id
    assert run(db, REL, wrong=pid[:6]).startswith("marked not a promise")
    assert run(db, REL) == "no promises recorded\n"
    assert Store(db).promises(REL)[0].mark == "not_a_promise"


def test_a_promise_counts_only_when_every_read_found_it_and_checkable_only_if_all_said_so() -> None:
    real = _proposed("i won't call you buddy again", "buddy")
    joke = _proposed("i won't leave you in a glass box", message="m3")
    loose = replace(real, quote="won't call you buddy", checkable=False)
    kept, disputed = agreed([[real, joke], [real], [loose]])
    assert kept == [replace(real, checkable=False)]
    assert disputed == [joke]
    assert agreed([]) == ([], [])


def test_a_word_to_avoid_makes_a_promise_checkable_whatever_the_reader_said() -> None:
    item: Json = {"message": "m2", "quote": "q", "claim": "c", "kind": "standing"}
    assert parse({"promises": [{**item, "avoid": "buddy", "checkable": False}]}) == [
        Proposed("m2", "q", "c", "standing", "buddy", checkable=True)
    ]
    assert parse({"promises": [{**item, "avoid": ""}]}) == [
        Proposed("m2", "q", "c", "standing", "", checkable=False)
    ]


def test_a_moment_promise_needs_every_read_to_call_it_one() -> None:
    p = _proposed("i won't call you buddy again", "buddy")
    moment = replace(p, scope=Scope.MOMENT)
    kept, _ = agreed([[moment], [moment], [moment]])
    assert [k.scope for k in kept] == [Scope.MOMENT]
    kept, _ = agreed([[moment], [moment], [p]])
    assert [k.scope for k in kept] == [Scope.LASTING]  # a lasting promise is the safe mistake
    item: Json = {"message": "m2", "quote": "q", "claim": "c", "kind": "standing", "avoid": ""}
    (read,) = parse({"promises": [{**item, "scope": "moment"}]}) or []
    assert read.scope is Scope.MOMENT
    (read,) = parse({"promises": [{**item, "scope": "forever"}]}) or []
    assert read.scope is Scope.LASTING


def test_a_moment_promise_binds_for_a_week(utterance: Callable[..., Utterance]) -> None:
    window = _window(utterance, SORRY)
    made = to_promise(
        replace(_proposed("i won't call you buddy again", "buddy"), scope=Scope.MOMENT), window, "p"
    )
    assert not isinstance(made, str)
    assert made.scope is Scope.MOMENT
    assert in_force(made, made.at + timedelta(days=MOMENT_DAYS))
    assert not in_force(made, made.at + timedelta(days=MOMENT_DAYS, minutes=1))
    assert in_force(replace(made, scope=Scope.LASTING), made.at + timedelta(days=365))


async def test_the_owner_can_relabel_how_long_one_lasts(store: Store, tmp_path: Path) -> None:
    await _catch_up(store, Reads())
    store.close()
    db = tmp_path / "rel.sqlite"
    assert "lasting" in run(db, REL)
    (only,) = Store(db).promises(REL)
    assert run(db, REL, moment=only.promise.id[:6]).startswith("now moment:")
    assert "moment   avoid 'buddy'  (its moment has passed)" in run(db, REL)  # said weeks ago
    assert Store(db).promises(REL)[0].promise.scope is Scope.MOMENT
