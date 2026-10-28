from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.card import Card
from companion.core.extractor import Extraction
from companion.core.turn.listening import ListeningRead
from companion.core.turn.now import KEY
from companion.core.types import Frame, Json, TraceId, TurnId
from companion.features.now.run import SENT, SHADOW, now_note, read_now
from companion.loops.current import Heard, Turn
from companion.loops.features import Lookups, Moment
from companion.loops.record import Recorder
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

CALM: Heard = (ListeningRead(severity=0, stance="other", vague=False, age_coded=False), "j", "p")
HEAVY: Heard = (ListeningRead(severity=2, stance="other", vague=False, age_coded=False), "j", "p")
LINE = (
    "[About 2 minutes ago they said dinner is coming soon."
    " It has not happened yet unless they say so.]"
)


class Reads:
    def __init__(self, now: str = "soon", what: str = "dinner is coming soon") -> None:
        self.answer: Json = {"now": now, "what": what, "minutes": 30}
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction(self.answer, "j", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(store: Store, phase: str, minutes_ago: int, what: str = "dinner is coming soon") -> None:
    detail: dict[str, Json] = {"phase": phase, "what": what, "minutes": 30, "said": "words"}
    at = NOW - timedelta(minutes=minutes_ago)
    Recorder(store, REL, SESSION, TurnId(f"t{minutes_ago}"), TraceId("x"), at).decide(KEY, detail)


def _note(store: Store, mode: str, frame: Frame = Frame.REAL) -> tuple[tuple[str, ...], list[str]]:
    runtime = Runtime(store, Talker(), PREFIX, REL, now=mode)
    t = Turn(SESSION, TurnId("t"), NOW, [], "lol out of all the things")
    offer = now_note(Moment(runtime, t, frame, CALM, Lookups(), False, []), None, {})
    for write in offer.after:
        write()
    logged = [d.reason for k in (SENT, SHADOW) for d in store.decisions_with_key(REL, k)]
    return offer.tail, logged


async def _read(store: Store, judge: Reads, heard: Heard | None, **kw: object) -> None:
    runtime = Runtime(store, Talker(), PREFIX, REL, judge=judge, **kw)  # type: ignore[arg-type]
    t = Turn(SESSION, TurnId("t"), NOW, [], "getting dinner soon")
    await read_now(runtime, t, Frame.REAL, heard, Card((), (), (), (), {}, NOW))


def test_what_they_said_is_coming_reaches_the_reply_while_it_is_open(store: Store) -> None:
    _said(store, "soon", 2)
    tail, logged = _note(store, "on")
    assert tail == (LINE,)
    assert len(logged) == 1


def test_in_shadow_the_note_is_logged_and_not_sent_and_off_does_nothing(store: Store) -> None:
    _said(store, "soon", 2)
    assert _note(store, "shadow") == ((), [f"{SHADOW}"])
    assert _note(store, "off")[0] == ()
    assert _note(store, "on", Frame.PLAY)[0] == ()


def test_once_they_say_it_happened_there_is_no_note(store: Store) -> None:
    _said(store, "soon", 10)
    _said(store, "done", 2, what="")
    assert _note(store, "on")[0] == ()


async def test_the_reader_logs_a_label_and_skips_serious_turns_and_none(store: Store) -> None:
    await _read(store, Reads(), CALM, now="shadow")
    assert [(d.detail or {}).get("phase") for d in store.decisions_with_key(REL, KEY)] == ["soon"]
    await _read(store, Reads(), HEAVY, now="on")
    await _read(store, Reads(now="none", what=""), CALM, now="on")
    assert len(store.decisions_with_key(REL, KEY)) == 1
    idle = Reads()
    await _read(store, idle, CALM, now="off", initiative=False)
    assert idle.calls == 0
