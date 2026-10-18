from __future__ import annotations

import httpx

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.evals.runner import _free  # pyright: ignore[reportPrivateUsage]
from companion.models.kiro import KiroTalker


def test_the_kiro_talker_turns_the_gateways_reasoning_off() -> None:
    talker = KiroTalker("k", httpx.AsyncClient(), "claude-sonnet-4.6")
    request = TalkerRequest(build_prefix("persona " * 600), (Message("user", "hi"),))
    body = talker.body(request)
    assert body["thinking"] == {"type": "disabled"}
    assert body["model"] == "claude-sonnet-4.6"


def test_free_endpoints_are_recognised_for_one_call_at_a_time() -> None:
    assert _free("kiro/claude-sonnet-4.6")
    assert _free("dots-studio/dots-3-note-preview:free")
    assert not _free("openai/gpt-6-luna")
    assert not _free(None)
