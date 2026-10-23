from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from pathlib import Path

import pytest
from tests.conftest import REL, T0

from companion.cli.promises import run
from companion.core.extractor import Extraction
from companion.core.promises import Proposed, to_promise
from companion.core.types import Frame, Json, Speaker, Utterance
from companion.features.openloops.run import Reading, catch_up_loops
from companion.store.sqlite.store import Store

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


def _proposed(quote: str, avoid: str = "", message: str = "m2") -> Proposed:
    return Proposed(message, quote, "The companion won't call them buddy.", "standing", avoid)


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
        store, model, REL, (T0, UTC), lambda r, d: None, Reading(40, 4, 1, promises=promises)
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
