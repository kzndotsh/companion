from __future__ import annotations

import dataclasses

import httpx

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, build_request, request_sha256
from companion.models.openrouter import OpenRouterTalker
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


def test_the_card_rides_a_system_block_after_the_cached_persona() -> None:
    from companion.models.wire import system_blocks  # noqa: PLC0415

    request = build_request(PREFIX, [], "hi", "[clock]", "[What you remember:\n- likes tea]")
    first, second = system_blocks(request)
    assert first["text"] == PREFIX.system
    assert first["cache_control"] == {"type": "ephemeral"}
    assert second == {"type": "text", "text": "[What you remember:\n- likes tea]"}
    assert "likes tea" not in request.messages[-1].content


def test_no_card_means_one_system_block() -> None:
    from companion.models.wire import system_blocks  # noqa: PLC0415

    assert len(system_blocks(build_request(PREFIX, [], "hi"))) == 1


def test_a_scene_reminder_is_the_last_message_and_part_of_the_request_identity() -> None:
    plain = build_request(PREFIX, [], "hi", "", "card")
    tailed = dataclasses.replace(plain, tail="be specific")
    talker = OpenRouterTalker("k", httpx.AsyncClient(), "deepseek/x")
    assert talker.body(tailed)["messages"][-1] == {"role": "system", "content": "be specific"}  # type: ignore[index]
    assert talker.body(plain)["messages"][-1]["role"] == "user"  # type: ignore[index]
    assert request_sha256(plain) != request_sha256(tailed)
