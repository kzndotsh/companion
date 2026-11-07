from __future__ import annotations

from collections.abc import Callable

from companion.core.turn.context import (
    Scored,
    conversation_prompt,
    inputs_hash,
    schema_hash,
    transcript_prompt,
)
from companion.core.types import Speaker, Utterance

C, U = Speaker.COMPANION, Speaker.USER


def test_the_prompt_has_the_last_eight_messages_and_the_newest(
    utterance: Callable[..., Utterance],
) -> None:
    hist = [utterance(text=f"m{i}", speaker=C if i % 2 == 0 else U) for i in range(10)]
    prompt = conversation_prompt(hist, "okie")
    assert "m1\n" not in prompt
    assert "[COMPANION] m2" in prompt
    assert prompt.endswith("Newest USER message: okie")


def test_the_bracket_shape_is_what_the_judges_were_measured_on(
    utterance: Callable[..., Utterance],
) -> None:
    hist = [utterance(text="hi", speaker=U), utterance(text="hey you", speaker=C)]
    assert conversation_prompt(hist, "ok") == (
        "Conversation:\n[USER] hi\n[COMPANION] hey you\n\nNewest USER message: ok"
    )


def test_the_colon_shape_and_a_preamble_keep_their_own_words() -> None:
    before = [(U, "hi"), (C, "hey you")]
    assert transcript_prompt(before, "ok", tags="colon") == (
        "Conversation:\nUSER: hi\nCOMPANION: hey you\n\nNewest USER message: ok"
    )
    assert transcript_prompt(before, "ok", preamble=["It is now Friday."]).startswith(
        "It is now Friday.\nConversation:\n[USER] hi"
    )


def test_a_window_takes_the_last_messages(utterance: Callable[..., Utterance]) -> None:
    hist = [utterance(text=f"m{i}", speaker=U) for i in range(5)]
    prompt = conversation_prompt(hist, "x", last=2)
    assert "m2" not in prompt
    assert "[USER] m3\n[USER] m4" in prompt


def test_the_detail_of_a_scored_judge_is_the_same_everywhere() -> None:
    got = Scored(0.5, "m", "the prompt")
    assert list(got.detail("p@v1", schema={"a": 1}, scores={"x": 1})) == [
        "scorer",
        "prompt",
        "schema_hash",
        "inputs_hash",
        "scores",
    ]
    detail = got.detail("p@v1", labels={})
    assert detail["inputs_hash"] == inputs_hash("the prompt")
    assert schema_hash({"b": 1, "a": 2}) == schema_hash({"a": 2, "b": 1})
    assert "schema_hash" not in detail
