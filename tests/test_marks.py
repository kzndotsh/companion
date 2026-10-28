"""/flag and /fav mark the latest reply, or the one they were sent as a reply to."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from companion.core.prompt.prefix import build_prefix
from companion.core.replay import TurnRecord
from companion.core.types import SessionId, TurnId
from companion.daemon import UNKNOWN_REPLY, chat_commands, delivery_hooks
from companion.settings import Settings
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "marks.sqlite")
    prefix = build_prefix("x " * 3000)
    store.save_prefix(prefix)
    for tid in ("older", "latest"):
        store.record_turn(
            TurnRecord(TurnId(tid), REL, SessionId("s"), prefix.sha256, "", "0" * 64, None, T0)
        )
    return store


def _marks(store: Store) -> Any:
    return chat_commands(store, REL, None, Settings.from_env({"COMPANION_PLATFORM": "discord"}))  # type: ignore[arg-type]


async def test_a_mark_sent_as_a_reply_lands_on_the_turn_of_that_message(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.record_message(REL, "discord", "m1", TurnId("older"), T0, sent=True)
    await _marks(store)["fav"]("this one", "m1")
    await _marks(store)["fav"]("and now", None)
    assert [(f.turn_id, f.note) for f in store.favorites(REL)] == [
        ("older", "this one"),
        ("latest", "and now"),
    ]


async def test_a_reply_to_a_message_it_never_kept_marks_nothing_and_says_so(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    assert await _marks(store)["fav"]("x", "unknown") == UNKNOWN_REPLY
    assert await _marks(store)["flag"]("x", "unknown") == UNKNOWN_REPLY
    assert store.favorites(REL) == []
    assert store.flags(REL) == []


def test_each_message_of_a_reply_is_kept_with_the_turn_just_stored(tmp_path: Path) -> None:
    store = _store(tmp_path)
    sent = delivery_hooks(store, REL, "k", "discord").on_sent
    assert sent is not None
    sent("p1")
    sent("p2")
    assert store.turn_of_message(REL, "discord", "p2") == "latest"
    assert store.turn_of_message(REL, "telegram", "p2") is None


async def test_a_mark_sent_as_a_reply_to_their_own_message_lands_on_its_turn(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.record_message(REL, "discord", "u1", TurnId("older"), T0, sent=False)
    await _marks(store)["flag"]("that reply", "u1")
    assert [f.turn_id for f in store.flags(REL)] == ["older"]
