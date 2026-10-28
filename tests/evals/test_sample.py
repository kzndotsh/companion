"""An eval sample is what the person would receive: the turn's own notes and reply checks."""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.recheck import DASHED, QUIP
from companion.core.talker import Reply
from companion.core.turn.ownup import NOTE as OWNED_NOTE
from companion.core.turn.questions import NOTE as QUESTION_NOTE
from companion.core.types import Frame, Json, Speaker, TraceId, TurnId, Utterance, UtteranceId
from companion.evals.fixtures import Fixture, MaxWords, Script
from companion.evals.runner import Models, Plan, Variant, run_eval
from companion.evals.sample import draw
from companion.features.basics.logic import ASKED as ASKED_NAME
from companion.kit.record import Recorder
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_chaos import Chaos
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION
from tests.turn.test_recheck_loop import Judge as TurnJudge

ASKING = (
    ("user", "back from the shops"),
    ("assistant", "ooh, anything good?"),
    ("user", "you said the shop was shut, it wasn't"),
    ("assistant", "oh, my bad, I mixed it up. was it busy?"),
    ("user", "packed"),
    ("assistant", "ugh, long queue?"),
)
DASH = "sure — sounds fine"
PLAIN = "sure, sounds fine"
JOKE = "ugh, crispy fries \U0001f62d the sandwich had to carry the meal on its own"


class Talker:
    """Answers with each of `replies` in turn and keeps every request."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies) or ["nice"]
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        text = self.replies[min(len(self.seen) - 1, len(self.replies) - 1)]
        return Reply(text, "m", 5, cost_usd=0.01)


class Quips:
    """The reply checks' judge: reads every reply as a joke bolted on, and counts its calls."""

    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"added_joke": self.calls == 1, "generic": False}, "j", 0.001, 1)


def _script(
    history: tuple[tuple[str, str], ...] = (),
    user: str = "yeah kinda",
    labels: tuple[int, str, bool, bool, bool] | None = (0, "other", False, False, False),
    clock: str = "",
    lore: tuple[str, ...] = (),
) -> Fixture:
    script = Script(history, user, clock=clock, labels=labels, lore=lore)
    return Fixture("s", "a script", (MaxWords(50),), script=script)


def _unvaried(text: str) -> str:
    """Without the length limit, which is varied per turn from its random id."""
    return re.sub(r"under about \d+ words", "under about N words", text)


async def _live(tmp_path: Path, f: Fixture, judge: Chaos | TurnJudge) -> TalkerRequest:
    """What the turn itself sends for the script's moment, over the same stored history."""
    assert f.script is not None
    store = Store(tmp_path / "live.sqlite")
    n = len(f.script.history)
    for i, (role, text) in enumerate(f.script.history):
        speaker = Speaker.USER if role == "user" else Speaker.COMPANION
        uid = uuid.uuid4().hex
        at = NOW - timedelta(minutes=n + 1 - i)
        store.append_utterance(
            Utterance(
                UtteranceId(uid), REL, SESSION, TurnId(uid), speaker, text, Frame.REAL, "t", at
            )
        )
    Recorder(store, REL, SESSION, TurnId("x"), TraceId("x"), NOW).decide(
        ASKED_NAME, at=NOW - timedelta(hours=1)
    )
    talker = Talker()
    await handle(Runtime(store, talker, PREFIX, REL, judge=judge), SESSION, f.script.user, "t", NOW)
    store.close()
    return talker.seen[0]


@pytest.mark.parametrize("labelled", [False, True])
async def test_a_scripted_sample_sends_what_the_turn_would(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, labelled: bool
) -> None:
    # the mark is drawn from the turn's random id, which differs between the two turns
    def never(seed: str, theirs: str) -> bool:
        del seed, theirs
        return False

    monkeypatch.setattr("companion.features.marks.run.offered", never)
    f = _script(ASKING, labels=(0, "other", False, False, False) if labelled else None)
    live = await _live(tmp_path, f, TurnJudge() if labelled else Chaos(0, only="raise"))
    clock = re.match(r"<clock>(.*?)</clock>", live.card)
    assert clock is not None
    assert f.script is not None
    f = _script(ASKING, labels=f.script.labels, clock=clock.group(1))
    talker = Talker()
    drawn = await draw(f, Variant("a", PREFIX, raw=True), None, talker, Quips())
    sent = drawn.request
    assert _unvaried(sent.card) == _unvaried(live.card)
    assert sent.messages == live.messages
    assert sent.tail == live.tail
    assert sent.tail == f"{OWNED_NOTE.text}\n{QUESTION_NOTE.text}"  # both after the history
    assert OWNED_NOTE.text not in sent.card


async def test_a_dashed_reply_is_drawn_again_unless_raw() -> None:
    f = _script()
    checked = await draw(f, Variant("a", PREFIX), None, Talker(DASH, PLAIN), Quips())
    assert (checked.reply.text, checked.redrawn) == (PLAIN, (DASHED,))
    raw = await draw(f, Variant("a", PREFIX, raw=True), None, Talker(DASH, PLAIN), Quips())
    assert (raw.reply.text, raw.redrawn) == (DASH, ())


async def test_the_quip_judge_runs_for_real_and_its_redraw_is_counted() -> None:
    f = _script(user="kinda too crispy/hard")
    judge = Quips()
    talker = Talker(JOKE, PLAIN)
    res = await run_eval(
        Plan([f], {}, [Variant("a", PREFIX)], 1, 1.0), Models(lambda m, e: talker, judge)
    )
    [s] = res.cells[("s", "a")].samples
    assert (s.reply, s.redrawn) == (PLAIN, (QUIP,))
    assert judge.calls == 1
    assert s.cost_usd == pytest.approx(0.021)  # two replies and the quip read
    assert len(talker.seen) == 2


async def test_a_recorded_turn_passes_the_same_checks() -> None:
    f = Fixture(
        "r", "recorded", (MaxWords(50),), turn="t1", labels=(0, "other", False, False, False)
    )
    base = TalkerRequest(PREFIX, (Message("user", "what are you up to"),), card="clock")
    drawn = await draw(f, Variant("a", PREFIX), base, Talker(DASH, PLAIN), Quips())
    assert drawn.request.card == "clock"
    assert (drawn.reply.text, drawn.redrawn) == (PLAIN, (DASHED,))


async def test_a_fixture_without_labels_gets_the_checks_a_turn_with_no_reading_gets() -> None:
    quips = Quips()
    drawn = await draw(_script(labels=None), Variant("a", PREFIX), None, Talker(DASH, PLAIN), quips)
    assert (drawn.reply.text, drawn.redrawn) == (PLAIN, (DASHED,))  # the code checks still run
    assert quips.calls == 0  # but not the judge, which reads only an ordinary turn


async def test_the_fixtures_lore_reaches_the_lore_note() -> None:
    f = _script(lore=("rainy afternoons are the best ones",))
    drawn = await draw(f, Variant("a", PREFIX, raw=True), None, Talker(), Quips())
    assert 'you said: "rainy afternoons are the best ones"' in drawn.request.card


async def test_a_tried_note_lands_where_its_switch_says() -> None:
    v = Variant("a", PREFIX, raw=True, card_notes=("[In the card.]",), tail_notes=("[After.]",))
    drawn = await draw(_script(ASKING), v, None, Talker(), Quips())
    sent = drawn.request
    assert sent.tail.endswith("\n[After.]")
    assert "After." not in sent.card
    notes = sent.card[sent.card.index("<notes>") :]
    assert "In the card." in notes
    assert "In the card." not in sent.tail


async def test_a_roleplay_variant_answers_as_a_scene() -> None:
    v = Variant("a", PREFIX, roleplay=True, scene="[Stay in the scene.]")
    drawn = await draw(_script(ASKING), v, None, Talker(), Quips())
    assert drawn.request.tail == "[Stay in the scene.]"  # no everyday tail notes in a scene
    assert "pretend" in drawn.request.card.lower()
