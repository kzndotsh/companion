from __future__ import annotations

from collections.abc import Callable

from companion.core.turn.context import build_prompt
from companion.core.types import Speaker, Utterance

C, U = Speaker.COMPANION, Speaker.USER


def test_the_prompt_has_the_last_eight_messages_and_the_newest(
    utterance: Callable[..., Utterance],
) -> None:
    hist = [utterance(text=f"m{i}", speaker=C if i % 2 == 0 else U) for i in range(10)]
    prompt = build_prompt(hist, "okie")
    assert "m1\n" not in prompt
    assert "[COMPANION] m2" in prompt
    assert prompt.endswith("Newest USER message: okie")
