from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.types import Speaker, Utterance
from companion.store.sqlite import ledger
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def _chat(conn: sqlite3.Connection, utterance: Callable[..., Utterance]) -> None:
    for i, (who, text) in enumerate(
        [(Speaker.USER, "hi"), (Speaker.COMPANION, "hello there"), (Speaker.USER, "how are you")]
    ):
        u = utterance(text=text, speaker=who, uid=f"u{i}")
        from dataclasses import replace  # noqa: PLC0415

        ledger.append_utterance(conn, replace(u, at=T0 + timedelta(seconds=i)))


def test_an_undelivered_reply_leaves_the_history(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _chat(conn, utterance)
    marked = ledger.mark_undelivered(conn, REL, "hello there", "status 429", T0)
    assert marked is not None
    seen = ledger.history_before(conn, REL, T0 + timedelta(hours=1), 10)
    assert [u.text for u in seen] == ["hi", "how are you"]


def test_it_stays_in_the_ledger_and_the_record_is_append_only(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _chat(conn, utterance)
    ledger.mark_undelivered(conn, REL, "hello there", "x", T0)
    assert conn.execute("SELECT COUNT(*) FROM utterances").fetchone()[0] == 3
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM undelivered")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE undelivered SET reason = 'y'")


def test_unknown_text_and_a_second_mark_do_nothing(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _chat(conn, utterance)
    assert ledger.mark_undelivered(conn, REL, "never said", "x", T0) is None
    assert ledger.mark_undelivered(conn, REL, "hello there", "x", T0) is not None
    assert ledger.mark_undelivered(conn, REL, "hello there", "x", T0) is None


def test_the_memory_step_does_not_read_a_reply_nobody_saw(
    conn: sqlite3.Connection, utterance: Callable[..., Utterance]
) -> None:
    _chat(conn, utterance)
    ledger.mark_undelivered(conn, REL, "hello there", "x", T0)
    assert [u.text for u in ledger.utterances_after(conn, REL, None, 10)] == ["hi", "how are you"]


def test_the_store_logs_the_decision_with_a_reason_written_by_code(
    tmp_path: object, utterance: Callable[..., Utterance]
) -> None:
    from pathlib import Path  # noqa: PLC0415

    store = Store(Path(str(tmp_path)) / "rel.sqlite")
    store.append_utterance(utterance(text="hi", uid="a"))
    reply = utterance(text="hello there", speaker=Speaker.COMPANION, uid="b")
    store.append_utterance(reply)
    marked = store.mark_undelivered(REL, "hello there", "status 429", T0 + timedelta(seconds=5))
    assert marked is not None
    reasons = [d.reason for d in store.decisions_for_turn(REL, marked.turn_id)]
    assert "reply not delivered, so it is left out of what the model reads" in reasons
    store.close()


def test_a_reply_cut_off_is_read_as_the_part_that_arrived(
    tmp_path: object, utterance: Callable[..., Utterance]
) -> None:
    from pathlib import Path  # noqa: PLC0415

    store = Store(Path(str(tmp_path)) / "rel.sqlite")
    store.append_utterance(utterance(text="hi", uid="a"))
    store.append_utterance(
        utterance(text="First bit. Second bit.", speaker=Speaker.COMPANION, uid="b")
    )
    seen = store.mark_partly_delivered(
        REL, "First bit. Second bit.", "First bit.", "superseded", T0 + timedelta(seconds=5)
    )
    assert seen is not None
    history = store.history_before(REL, T0 + timedelta(days=1), 10)
    assert [u.text for u in history] == ["hi", "First bit."]
    assert history[-1].turn_id == seen.turn_id and history[-1].speaker is Speaker.COMPANION
    keys = [d.key for d in store.decisions_for_turn(REL, seen.turn_id)]
    assert "reply partly delivered" in keys  # the whole reply stays in the ledger, marked
    store.close()
