from __future__ import annotations

import pytest

from companion.core.prompt.prefix import (
    MIN_PREFIX_TOKENS,
    PrefixTooShortError,
    Tool,
    build_prefix,
    canonical_text,
)
from companion.core.prompt.request import Message, build_request

PERSONA = ("She keeps her sentences short and lowercases when relaxed. " * 80).strip()


def test_same_inputs_give_the_same_bytes_and_hash() -> None:
    a, b = build_prefix(PERSONA), build_prefix(PERSONA)
    assert a == b
    assert len(a.sha256) == 64


def test_whitespace_noise_does_not_change_the_hash() -> None:
    noisy = PERSONA.replace(". ", ".  \r\n") + "   \n\n\n"
    clean = PERSONA.replace(". ", ".\n")
    assert build_prefix(noisy).sha256 == build_prefix(clean).sha256


def test_unicode_composition_does_not_change_the_hash() -> None:
    composed = PERSONA + " café"
    decomposed = PERSONA + " café"
    assert build_prefix(composed).sha256 == build_prefix(decomposed).sha256


def test_tool_order_and_key_order_do_not_change_the_hash() -> None:
    t1 = Tool("remember", "store a thing", {"type": "object", "properties": {"a": 1, "b": 2}})
    t2 = Tool("recall", "pull a thing", {"properties": {"b": 2, "a": 1}, "type": "object"})
    t1b = Tool("remember", "store a thing", {"properties": {"b": 2, "a": 1}, "type": "object"})
    assert build_prefix(PERSONA, [t1, t2]).sha256 == build_prefix(PERSONA, [t2, t1b]).sha256


def test_a_changed_persona_or_tool_changes_the_hash() -> None:
    base = build_prefix(PERSONA)
    assert build_prefix(PERSONA + " never says synergy.").sha256 != base.sha256
    tool = Tool("recall", "pull a thing", {})
    assert build_prefix(PERSONA, [tool]).sha256 != base.sha256


def test_a_prefix_below_the_cache_minimum_is_refused() -> None:
    with pytest.raises(PrefixTooShortError, match=str(MIN_PREFIX_TOKENS)):
        build_prefix("too short")


def test_volatile_context_rides_the_user_message_and_never_touches_the_prefix() -> None:
    prefix = build_prefix(PERSONA)
    history = [Message("user", "hey"), Message("assistant", "hey yourself")]
    quiet = build_request(prefix, history, "buried in admin today")
    loud = build_request(
        prefix, history, "buried in admin today", volatile="[plates] grant decision due ~Nov 1"
    )
    assert quiet.prefix.sha256 == loud.prefix.sha256
    assert quiet.messages[:-1] == loud.messages[:-1]
    assert "grant decision" in loud.messages[-1].content
    assert loud.messages[-1].content.endswith("buried in admin today")


def test_the_request_has_no_thinking_knob() -> None:
    fields = set(build_request(build_prefix(PERSONA), [], "hi").__dataclass_fields__)
    assert fields == {"prefix", "messages", "card"}


def test_canonical_text_ends_with_exactly_one_newline() -> None:
    assert canonical_text("a  \n\n\n") == "a\n"


def test_a_request_without_a_card_hashes_as_before_the_card_existed() -> None:
    import hashlib  # noqa: PLC0415
    import json  # noqa: PLC0415

    from companion.core.prompt.request import request_sha256  # noqa: PLC0415

    prefix = build_prefix(PERSONA)
    plain = build_request(prefix, [], "hi")
    old = json.dumps(
        {"prefix": prefix.sha256, "messages": [["user", "hi"]]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert request_sha256(plain) == hashlib.sha256(old.encode()).hexdigest()
    assert request_sha256(plain) != request_sha256(build_request(prefix, [], "hi", card="[m]"))
