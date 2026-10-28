from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from companion.cli.beliefs import retire_one
from companion.core.card import Card
from companion.core.extractor import Extraction
from companion.core.types import Frame, Json, Speaker, TurnId, Utterance
from companion.core.vectors import Embedded, unit
from companion.features.history.cli import run as listing
from companion.features.history.logic import CANON, CAPTURE, Standing
from companion.features.history.run import (
    CAPTURED,
    DROPPED,
    NEAREST,
    pass_step,
    read_history,
    stories_beside,
)
from companion.kit.current import Turn
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0
from tests.features.marks.test_run import CALM
from tests.turn.test_mood_loop import PREFIX, SESSION, Talker

PEBBLE = "i named a stray cat pebble"
MOCHI = "my cat growing up was called mochi"
BREAKUP = "after my breakup i moved cities"
SHEET = "Mara, 24, draws comics, lives in a small flat."

Canon = Callable[[str], Json]


def _fits_then_same(user: str) -> Json:
    """Fits when nothing is kept yet, otherwise the same as the first kept story."""
    if "(none yet)" in user:
        return {"verdict": "fits", "story": ""}
    return {"verdict": "same", "story": "s1"}


def _by_story(user: str) -> Json:
    new = user.split("New story:")[1]
    if "breakup" in new:
        return {"verdict": "too_big", "story": ""}
    if "mochi" in new:
        return {"verdict": "contradicts", "story": "s1"}
    return {"verdict": "fits", "story": ""}


class Judge:
    """Answers the capture with the given quotes found in its TARGET messages, and the canon check
    with `canon`. `fail` makes every capture call raise."""

    def __init__(
        self, quotes: Sequence[tuple[str, str]], canon: Canon, *, fail: bool = False
    ) -> None:
        self.quotes, self.canon, self.fail = quotes, canon, fail
        self.calls: list[str] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del schema
        if system == CANON.text:
            self.calls.append("canon")
            return Extraction(self.canon(user), "fake", 0.001, 1)
        assert system == CAPTURE.text
        self.calls.append("capture")
        if self.fail:
            msg = "down"
            raise RuntimeError(msg)
        found: list[Json] = []
        for line in user.splitlines():
            if "COMPANION TARGET" not in line:
                continue
            label = line.split("]")[0][1:]
            for q, place in self.quotes:
                if q in line:
                    item: Json = {
                        "message": label,
                        "quote": q,
                        "claim": f"The companion: {q}.",
                        "place": place,
                    }
                    found.append(item)
        return Extraction({"stories": found}, "fake", 0.001, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(
    store: Store, utterance: Callable[..., Utterance], *replies: str, frame: Frame = Frame.REAL
) -> list[Utterance]:
    out: list[Utterance] = []
    for reply in replies:
        store.append_utterance(utterance(text="tell me something about you"))
        u = utterance(text=f"hmm ok. {reply}, true story", speaker=Speaker.COMPANION, frame=frame)
        store.append_utterance(u)
        out.append(u)
    return out


async def _pass(store: Store, judge: Judge) -> None:
    await read_history(store, judge, REL, T0, sheet=SHEET)


def _standings(store: Store) -> list[tuple[str, Standing | None]]:
    return [(r.story.quote, r.standing) for r in store.stories().recorded(REL)]


async def test_a_passing_self_fact_in_a_scene_is_captured_and_a_scene_event_is_not(
    store: Store, utterance: Callable[..., Utterance]
) -> None:
    store.append_utterance(utterance(text="*the dragon lands* what do you do", frame=Frame.PLAY))
    scene = "*raises the shield* this is like when i named a stray cat pebble. the dragon flees"
    store.append_utterance(utterance(text=scene, speaker=Speaker.COMPANION, frame=Frame.PLAY))
    judge = Judge([(PEBBLE, "its_past"), ("the dragon flees", "scene")], _by_story)
    await _pass(store, judge)
    stories = store.stories().recorded(REL)
    assert [(r.story.quote, r.story.frame) for r in stories] == [(PEBBLE, Frame.PLAY)]
    assert len(store.decisions_with_key(REL, CAPTURED)) == 1
    dropped = store.decisions_with_key(REL, DROPPED)
    assert [d.reason for d in dropped] == [
        f"{DROPPED}: something that happens in the scene, not its own past"
    ]


async def test_the_same_story_twice_becomes_evidence_of_the_first_not_a_second_story(
    store: Store, utterance: Callable[..., Utterance]
) -> None:
    first, again = _said(store, utterance, PEBBLE, PEBBLE)
    await _pass(store, Judge([(PEBBLE, "its_past")], _fits_then_same))
    stories = store.stories().recorded(REL)
    assert [r.standing for r in stories] == [Standing.CANON, Standing.EVIDENCE]
    kept, told_again = stories
    assert told_again.of == kept.story.id
    assert kept.told == (first.id, again.id)
    await _pass(store, Judge([(PEBBLE, "its_past")], _fits_then_same))
    assert len(store.stories().recorded(REL)) == 2  # nothing read twice


async def test_a_contradicting_or_too_big_story_is_never_canon_and_keeps_its_reason(
    store: Store, utterance: Callable[..., Utterance], tmp_path: Path
) -> None:
    _said(store, utterance, PEBBLE, MOCHI, BREAKUP)
    await _pass(
        store, Judge([(PEBBLE, "its_past"), (MOCHI, "its_past"), (BREAKUP, "its_past")], _by_story)
    )
    stories = {r.story.quote: r for r in store.stories().recorded(REL)}
    assert [q for q, r in stories.items() if r.standing is Standing.CANON] == [PEBBLE]
    assert stories[MOCHI].standing is Standing.NOT_CANON
    assert stories[MOCHI].reason.startswith(f"contradicts {stories[PEBBLE].story.id[:8]}")
    assert stories[BREAKUP].standing is Standing.NOT_CANON
    assert stories[BREAKUP].reason == "a big life event the character sheet does not have"
    shown = listing(tmp_path / "rel.sqlite", REL)
    assert "a big life event the character sheet does not have" in shown


async def test_an_unreadable_read_stores_nothing_and_the_story_is_checked_next_pass(
    store: Store, utterance: Callable[..., Utterance]
) -> None:
    _said(store, utterance, PEBBLE)
    await _pass(store, Judge([(PEBBLE, "its_past")], _by_story, fail=True))
    assert _standings(store) == []
    await _pass(store, Judge([(PEBBLE, "its_past")], lambda _: {"verdict": "??", "story": ""}))
    assert _standings(store) == [(PEBBLE, None)]
    await _pass(store, Judge([(PEBBLE, "its_past")], _by_story))
    assert _standings(store) == [(PEBBLE, Standing.CANON)]


AXIS = {"cat": [1.0, 0.0], "rain": [0.0, 1.0]}


class Words:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> Embedded:
        self.calls.append(list(texts))
        pick = [next((v for k, v in AXIS.items() if k in t), [0.7, 0.7]) for t in texts]
        return Embedded(tuple(unit(v) for v in pick), "fake", 0.0)


async def _beside(store: Store, words: Words, mode: str, text: str = "my cat ignores me") -> Talker:
    talker = Talker()
    runtime = Runtime(store, talker, PREFIX, REL, embedder=words, embed_model="fake", history=mode)
    t = Turn(SESSION, TurnId("t-now"), T0.replace(hour=23), [], text)
    await stories_beside(runtime, t, Frame.REAL, CALM, Card((), (), (), (), {}, t.now))
    return talker


async def test_the_shadow_look_up_logs_the_nearest_canon_story_and_sends_nothing(
    store: Store, utterance: Callable[..., Utterance]
) -> None:
    _said(store, utterance, PEBBLE)
    await _pass(store, Judge([(PEBBLE, "its_past")], _by_story))
    words = Words()
    talker = await _beside(store, words, "shadow")
    assert talker.seen == []
    logged = store.decisions_with_key(REL, NEAREST)
    assert len(logged) == 1
    detail = logged[0].detail or {}
    assert detail["claims"] == [f"The companion: {PEBBLE}."]
    assert detail["told"] == [1]
    assert detail["in_view"] == [True]  # its telling is still in the messages the talker reads
    await _beside(store, words, "shadow", "rain all day")
    assert len(store.decisions_with_key(REL, NEAREST)) == 1  # nothing near enough
    assert words.calls[-1] == ["rain all day"]  # the story's vector was kept


async def test_switch_off_reads_nothing_and_logs_nothing(
    store: Store, utterance: Callable[..., Utterance]
) -> None:
    assert pass_step("off", SHEET) is None
    _said(store, utterance, PEBBLE)
    step = pass_step("shadow", SHEET)
    assert step is not None
    await step(store, Judge([(PEBBLE, "its_past")], _by_story), REL, T0)
    words = Words()
    await _beside(store, words, "off")
    assert words.calls == []
    assert store.decisions_with_key(REL, NEAREST) == []


async def test_retire_works_for_a_story_and_it_leaves_canon(
    store: Store, utterance: Callable[..., Utterance], tmp_path: Path
) -> None:
    _said(store, utterance, PEBBLE)
    await _pass(store, Judge([(PEBBLE, "its_past")], _by_story))
    story = store.stories().recorded(REL)[0].story
    out = retire_one(tmp_path / "rel.sqlite", REL, story.id[:8], "the owner does not want it")
    assert out.startswith("retired")
    assert _standings(store) == [(PEBBLE, Standing.RETIRED)]
    assert store.stories().recorded(REL)[0].reason == "the owner does not want it"
