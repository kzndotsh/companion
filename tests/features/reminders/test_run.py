from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Frame, Json, Speaker, TurnId, Utterance, UtteranceId
from companion.features.reminders.logic import Kind
from companion.features.reminders.run import ASKED, CANCELLED, SET, deliver_due
from companion.features.reminders.store import Reminder
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker

# NOW is Monday 19 Oct 2026, 17:00 UTC: 13:00 in New York


class Reminding(Judge):
    """Reads every message it is asked about as the reminder request it was given."""

    def __init__(self, slots: dict[str, Json] | None = None) -> None:
        super().__init__()
        self.slots, self.read = slots, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and "thing" in props:
            self.read += 1
            return Extraction(self.slots, "j", 0.0, 1)
        return await super().extract(system, user, schema)


def _slots(**kw: Json) -> dict[str, Json]:
    return {
        "ask": "set",
        "kind": "reminder",
        "thing": "take the dog out",
        "day": "unsaid",
        "ampm": "unsaid",
        "part": "unsaid",
        "repeats": False,
    } | kw


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    monkeypatch.setenv("TZ", "America/New_York")
    return Store(tmp_path / "rel.sqlite")


async def _say(store: Store, judge: Judge, text: str, at: datetime = NOW) -> str:
    talker = Talker()
    await handle(Conversation(store, talker, PREFIX, REL, judge=judge), SESSION, text, "t", at)
    return talker.seen[0].card


def _reasons(store: Store) -> list[str]:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=9), 50)}
    return [d.reason for t in turns for d in store.decisions_for_turn(REL, t)]


async def test_a_clear_request_is_stored_and_the_reply_is_told_the_time(store: Store) -> None:
    judge = Reminding(_slots(hour=8, ampm="pm"))
    card = await _say(store, judge, "remind me at 8pm to take the dog out")
    assert "It is set for tonight at 8:00 pm" in card
    [r] = store.reminders(REL)
    assert (r.state, r.kind, r.thing) == ("pending", Kind.REMINDER, "take the dog out")
    assert r.due_at == datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
    assert r.quote == "remind me at 8pm to take the dog out"
    assert SET in _reasons(store)


async def test_an_unclear_time_stores_nothing_asks_and_reads_the_answer(store: Store) -> None:
    judge = Reminding(_slots(day="tomorrow", hour=8))
    card = await _say(store, judge, "remind me tomorrow at 8 about the dog")
    assert "whether they meant 8 in the morning or the evening" in card
    assert store.reminders(REL) == []
    assert ASKED in _reasons(store)
    judge.slots = _slots(day="tomorrow", hour=8, part="morning")
    await _say(store, judge, "morning", NOW + timedelta(minutes=1))
    assert judge.read == 2  # no reminder words, but it had just asked when
    [r] = store.reminders(REL)
    assert r.local_wall == "2026-10-20 08:00"


async def test_ordinary_messages_are_not_read_and_a_repeating_one_is_asked(store: Store) -> None:
    judge = Reminding(_slots(hour=8, ampm="pm", repeats=True))
    await _say(store, judge, "long day, going to bed soon")
    assert judge.read == 0
    card = await _say(store, judge, "remind me every night at 8pm to take my meds")
    assert "only one-off reminders" in card
    assert store.reminders(REL) == []


async def test_a_cancel_drops_the_pending_one(store: Store) -> None:
    await _say(store, Reminding(_slots(hour=8, ampm="pm")), "remind me at 8pm to walk the dog")
    gone = Reminding(_slots(ask="cancel", thing="the dog"))
    card = await _say(store, gone, "actually cancel the dog reminder", NOW + timedelta(minutes=2))
    assert "You dropped the reminder" in card
    assert [r.state for r in store.reminders(REL)] == ["cancelled"]
    assert CANCELLED in _reasons(store)


class Writer(Talker):
    def __init__(self, *texts: str, fail: bool = False) -> None:
        super().__init__(fail=fail)
        self.texts = list(texts)

    async def reply(self, request: TalkerRequest) -> Reply:
        await super().reply(request)
        return Reply(text=self.texts.pop(0) if self.texts else "", model="fake", latency_ms=1)


def _due(store: Store, due: datetime, rid: str = "r1") -> None:
    store.add_reminder(
        Reminder(
            rid,
            REL,
            Kind.REMINDER,
            "the dog",
            "remind me about the dog",
            due,
            "",
            "America/New_York",
            TurnId("t0"),
            due - timedelta(hours=1),
        )
    )


def _user(store: Store, text: str, frame: Frame, at: datetime) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId(f"u-{at.timestamp()}"),
            REL,
            SESSION,
            TurnId(f"t-{at.timestamp()}"),
            Speaker.USER,
            text,
            frame,
            "t",
            at,
        )
    )


async def _deliver(
    store: Store, talker: Talker, now: datetime, started: datetime = NOW - timedelta(days=1)
) -> list[str]:
    out: list[str] = []

    async def send(text: str) -> None:
        out.append(text)

    await deliver_due(Conversation(store, talker, PREFIX, REL), send, SESSION, now, started)
    return out


async def test_a_due_reminder_is_written_in_its_voice_sent_once_and_stored(store: Store) -> None:
    _due(store, NOW)
    talker = Writer("hey, the dog needs out 🐕")
    assert await _deliver(store, talker, NOW + timedelta(minutes=1)) == [
        "hey, the dog needs out 🐕"
    ]
    assert "remind them about the dog" in talker.seen[0].tail
    assert [r.state for r in store.reminders(REL)] == ["sent"]
    said = store.history_before(REL, NOW + timedelta(hours=1), 10)
    assert [(u.speaker, u.text) for u in said] == [(Speaker.COMPANION, "hey, the dog needs out 🐕")]
    assert await _deliver(store, Writer("again"), NOW + timedelta(minutes=2)) == []


async def test_not_yet_due_waits(store: Store) -> None:
    _due(store, NOW + timedelta(hours=1))
    assert await _deliver(store, Writer("x"), NOW) == []
    assert [r.state for r in store.reminders(REL)] == ["pending"]


async def test_a_scene_holds_it_until_the_scene_ends_then_it_goes_late(store: Store) -> None:
    _due(store, NOW)
    _user(store, "*leans closer*", Frame.PLAY, NOW - timedelta(minutes=5))
    assert await _deliver(store, Writer("x"), NOW + timedelta(minutes=1)) == []
    assert [r.state for r in store.reminders(REL)] == ["pending"]
    _user(store, "ok back to real life", Frame.REAL, NOW + timedelta(hours=3))
    later = NOW + timedelta(hours=3, minutes=1)
    assert await _deliver(store, Writer("the dog!"), later) == ["the dog!"]
    assert [r.state for r in store.reminders(REL)] == ["late"]


async def test_one_missed_while_the_bot_was_down_is_let_go(store: Store) -> None:
    _due(store, NOW - timedelta(hours=5))
    assert await _deliver(store, Writer("x"), NOW, started=NOW - timedelta(minutes=1)) == []
    assert [r.state for r in store.reminders(REL)] == ["expired"]


async def test_a_failed_check_draws_once_more_and_a_silent_talker_sends_their_words(
    store: Store,
) -> None:
    _due(store, NOW, "r1")
    assert await _deliver(store, Writer("the dog — now", "the dog, now"), NOW) == ["the dog, now"]
    _due(store, NOW, "r2")
    assert await _deliver(store, Writer(fail=True), NOW) == ["⏰ the dog"]


async def test_a_failed_send_leaves_it_pending_for_the_next_tick(store: Store) -> None:
    _due(store, NOW)

    async def broken(text: str) -> None:
        del text
        msg = "telegram down"
        raise RuntimeError(msg)

    await deliver_due(
        Conversation(store, Writer("x"), PREFIX, REL), broken, SESSION, NOW, NOW - timedelta(days=1)
    )
    assert [r.state for r in store.reminders(REL)] == ["pending"]
    assert store.history_before(REL, NOW + timedelta(hours=1), 10) == []
