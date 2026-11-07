"""What the dispatchers decide for every feature, so a hook never checks it: its switch, a judge,
and whether its step after the turn holds the reply."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from tests.runtime import make_runtime
from tests.turn.test_mood_loop import NOW, PREFIX, REL, Talker

from companion.core import switch
from companion.core.extractor import Extraction
from companion.core.turn.listening import ListeningRead
from companion.core.types import (
    Frame,
    Json,
    Severity,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
    is_heavy,
)
from companion.kit import features as kit_features
from companion.kit.beside import settled
from companion.kit.current import Heard, Turn
from companion.kit.features import Feature, Moment, NoteName, Offer, Offered
from companion.registry import FEATURES
from companion.store.sqlite.store import Store
from companion.turn import beside as turn_beside
from companion.turn import notes, persist


class Judge:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        return Extraction(None, "j", 0.0, 1)


def _heard(severity: Severity) -> Heard:
    read = ListeningRead(severity=severity, stance="other", vague=False, age_coded=False)
    return Heard(read, "j", "p")


def _moment(
    tmp_path: Path, *, judge: bool = False, heard: Heard | None = None, **modes: str
) -> Moment:
    store = Store(tmp_path / "r.sqlite")
    c = make_runtime(store, Talker(), PREFIX, REL, judge=Judge() if judge else None, **modes)
    return Moment(c, Turn(TurnId("t"), NOW, [], "hi"), Frame.REAL, heard)


def _said() -> Utterance:
    return Utterance(
        UtteranceId("u"), REL, TurnId("t"), Speaker.USER, "hi", Frame.REAL, "test", NOW
    )


def test_a_switch_that_is_off_leaves_the_feature_out_and_shadow_or_on_does_not(
    tmp_path: Path,
) -> None:
    f = Feature("x", switch=switch.MOOD)
    assert not f.live(_moment(tmp_path, mood="off").c)
    assert f.live(_moment(tmp_path, mood="shadow").c)
    assert f.live(_moment(tmp_path, mood="on").c)
    assert Feature("y").live(_moment(tmp_path).c)  # no switch: always


def test_a_feature_that_needs_a_judge_is_left_out_of_a_runtime_without_one(tmp_path: Path) -> None:
    needs = Feature("x", needs_judge=True)
    assert not needs.can_read(_moment(tmp_path).c)
    assert needs.can_read(_moment(tmp_path, judge=True).c)
    assert Feature("y").can_read(_moment(tmp_path).c)


def test_a_note_comes_back_empty_while_its_switch_is_off(tmp_path: Path) -> None:
    f = Feature("x", note=lambda m, found, so_far: Offer(("line",)), switch=switch.MOOD)
    assert f.offer(_moment(tmp_path, mood="on"), None, Offered({})).lines == ("line",)
    assert f.offer(_moment(tmp_path, mood="off"), None, Offered({})).lines == ()


def test_the_moment_states_one_policy_for_a_turn_that_could_not_be_read(tmp_path: Path) -> None:
    unread, calm, heavy = (
        _moment(tmp_path, heard=h)
        for h in (None, _heard(Severity.TRIVIAL), _heard(Severity.SERIOUS))
    )
    assert [m.heavy for m in (unread, calm, heavy)] == [False, False, True]
    assert [m.unread_or_heavy for m in (unread, calm, heavy)] == [True, False, True]
    assert is_heavy(None, unread=True) and not is_heavy(None, unread=False)
    assert not unread.casual and calm.casual and not heavy.casual


async def test_the_step_after_the_turn_runs_beside_the_reply_unless_it_must_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = asyncio.Event()
    done: list[str] = []

    async def slow(m: Moment, said: Utterance, sent: str | None) -> None:
        del m, said, sent
        await release.wait()
        done.append("slow")

    async def keep(m: Moment, said: Utterance, sent: str | None) -> None:
        del m, said, sent
        done.append("keep")

    monkeypatch.setattr(
        persist,
        "FEATURES",
        (Feature("a", after_turn=slow), Feature("b", after_turn=keep, must_finish=True)),
    )
    await asyncio.wait_for(persist.after_turn(_moment(tmp_path), _said(), "ok"), 1)
    assert done == ["keep"]  # the reply is not held up by the one that is not waited for
    release.set()
    await settled()
    assert done == ["keep", "slow"]


async def test_a_shadow_look_up_of_a_feature_that_is_off_never_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[str] = []

    async def look(m: Moment) -> None:
        del m
        ran.append("ran")

    monkeypatch.setattr(turn_beside, "FEATURES", (Feature("x", shadow=look, switch=switch.MOOD),))
    turn_beside.shadows(_moment(tmp_path, mood="off"))
    turn_beside.shadows(_moment(tmp_path, mood="shadow"))
    await settled()
    assert ran == ["ran"]


def test_every_look_up_states_how_long_it_waits_and_stays_under_the_shared_deadline() -> None:
    notes.check_look_seconds()
    waits = {f.name: f.look_seconds for f in FEATURES if f.look is not None}
    assert waits and all(
        s is not None and 0 < s <= kit_features.LOOKS_TOGETHER_SECONDS for s in waits.values()
    )


def test_a_look_up_with_no_limit_or_one_past_the_deadline_stops_the_bot_at_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def look(m: Moment) -> None:
        del m

    for seconds in (None, kit_features.LOOKS_TOGETHER_SECONDS + 1):
        monkeypatch.setattr(notes, "FEATURES", (Feature("x", look=look, look_seconds=seconds),))
        with pytest.raises(RuntimeError, match="no limit"):
            notes.check_look_seconds()


def test_each_note_name_is_one_note_and_a_feature_note_is_named_by_it() -> None:
    assert len({n.value for n in NoteName}) == len(NoteName)
    assert set(notes.ORDER) == set(NoteName)
    named = {f.name for f in FEATURES if f.note is not None}
    assert named <= set(NoteName)
