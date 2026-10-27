from __future__ import annotations

from companion.core.turn.quoted import MAX_CHARS, Quoted, quoted_note
from companion.core.types import Speaker


def test_no_reply_and_an_empty_message_add_nothing() -> None:
    assert quoted_note(None) is None
    assert quoted_note(Quoted("  ", Speaker.USER)) is None


def test_the_note_quotes_each_line_and_says_whose_it_was() -> None:
    mine = quoted_note(Quoted("your call\nbaby", Speaker.COMPANION))
    theirs = quoted_note(Quoted("kettle's on", Speaker.USER))
    assert mine is not None
    assert theirs is not None
    assert "> your call\n> baby" in mine
    assert "your messages" in mine
    assert "their own" in theirs


def test_a_long_message_is_cut() -> None:
    note = quoted_note(Quoted("a" * (MAX_CHARS + 100), Speaker.USER))
    assert note is not None
    assert "a" * MAX_CHARS + "…" in note
    assert "a" * (MAX_CHARS + 1) not in note
