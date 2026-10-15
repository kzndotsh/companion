from __future__ import annotations

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, build_request
from companion.models.wire import messages_with_breakpoint

PREFIX = build_prefix("persona " * 800)


def test_breakpoint_sits_on_the_last_history_message_only() -> None:
    history = [Message("user", "a"), Message("assistant", "b")]
    wire = messages_with_breakpoint(build_request(PREFIX, history, "c", "[Mon 09:00]"))
    assert wire[1]["content"] == [
        {"type": "text", "text": "b", "cache_control": {"type": "ephemeral"}}
    ]
    assert wire[0]["content"] == "a"
    assert wire[2]["content"] == "[Mon 09:00]\n\nc"


def test_first_turn_has_no_breakpoint() -> None:
    wire = messages_with_breakpoint(build_request(PREFIX, [], "hi"))
    assert wire == [{"role": "user", "content": "hi"}]


def test_history_bytes_do_not_change_when_the_user_turn_changes() -> None:
    history = [Message("user", "a"), Message("assistant", "b")]
    one = messages_with_breakpoint(build_request(PREFIX, history, "c", "[x]"))
    two = messages_with_breakpoint(build_request(PREFIX, history, "d", "[y]"))
    assert one[:2] == two[:2]
